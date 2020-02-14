import warnings
from typing import Any, Awaitable, Callable, Coroutine, Optional, Union

import trio
from hypercorn.config import Config as HyperConfig
from hypercorn.trio import serve
from quart import Quart, request_started, websocket_started
from quart.ctx import RequestContext, WebsocketContext
from quart.logging import create_serving_logger
from quart.utils import is_coroutine_function
from quart.wrappers import Request, Response, Websocket

from .asgi import TrioASGIHTTPConnection, TrioASGILifespan, TrioASGIWebsocketConnection
from .request import TrioRequest, TrioWebsocket
from .response import TrioResponse
from .testing import TrioQuartClient
from .utils import run_sync


class QuartTrio(Quart):
    asgi_http_class = TrioASGIHTTPConnection
    asgi_lifespan_class = TrioASGILifespan  # type: ignore
    asgi_websocket_class = TrioASGIWebsocketConnection
    lock_class = trio.Lock
    request_class = TrioRequest
    response_class = TrioResponse
    test_client_class = TrioQuartClient
    websocket_class = TrioWebsocket

    def run(  # type: ignore
        self,
        host: str = "127.0.0.1",
        port: int = 5000,
        debug: Optional[bool] = None,
        use_reloader: bool = True,
        ca_certs: Optional[str] = None,
        certfile: Optional[str] = None,
        keyfile: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Run this application.

        This is best used for development only, see using Gunicorn for
        production servers.

        Arguments:
            host: Hostname to listen on. By default this is loopback
                only, use 0.0.0.0 to have the server listen externally.
            port: Port number to listen on.
            debug: If set enable (or disable) debug mode and debug output.
            use_reloader: Automatically reload on code changes.
            ca_certs: Path to the SSL CA certificate file.
            certfile: Path to the SSL certificate file.
            ciphers: Ciphers to use for the SSL setup.
            keyfile: Path to the SSL key file.
        """
        if kwargs:
            warnings.warn(
                f"Additional arguments, {','.join(kwargs.keys())}, are not supported.\n"
                "They may be supported by Hypercorn, which is the ASGI server Quart "
                "uses by default. This method is meant for development and debugging."
            )

        scheme = "https" if certfile is not None and keyfile is not None else "http"
        print(f"Running on {scheme}://{host}:{port} (CTRL + C to quit)")  # noqa: T001, T002

        trio.run(self.run_task, host, port, debug, use_reloader, ca_certs, certfile, keyfile)

    def run_task(
        self,
        host: str = "127.0.0.1",
        port: int = 5000,
        debug: Optional[bool] = None,
        use_reloader: bool = True,
        ca_certs: Optional[str] = None,
        certfile: Optional[str] = None,
        keyfile: Optional[str] = None,
        shutdown_trigger: Optional[Callable[..., Awaitable[None]]] = None,
    ) -> Coroutine[None, None, None]:
        """Return a task that when awaited runs this application.

        This is best used for development only, see Hypercorn for
        production servers.

        Arguments:
            host: Hostname to listen on. By default this is loopback
                only, use 0.0.0.0 to have the server listen externally.
            port: Port number to listen on.
            debug: If set enable (or disable) debug mode and debug output.
            use_reloader: Automatically reload on code changes.
            loop: Asyncio loop to create the server in, if None, take default one.
                If specified it is the caller's responsibility to close and cleanup the
                loop.
            ca_certs: Path to the SSL CA certificate file.
            certfile: Path to the SSL certificate file.
            keyfile: Path to the SSL key file.

        """
        config = HyperConfig()
        config.access_log_format = "%(h)s %(r)s %(s)s %(b)s %(D)s"
        config.access_logger = create_serving_logger()  # type: ignore
        config.bind = [f"{host}:{port}"]
        config.ca_certs = ca_certs
        config.certfile = certfile
        if debug is not None:
            config.debug = debug
        config.error_logger = config.access_logger  # type: ignore
        config.keyfile = keyfile
        config.use_reloader = use_reloader

        return serve(self, config)

    def ensure_async(self, func: Callable[..., Any]) -> Callable[..., Awaitable[Any]]:
        """Ensure that the returned func is async and calls the func.

        .. versionadded:: 0.11

        Override if you wish to change how synchronous functions are
        run. Before Quart 0.11 this did not run the synchronous code
        in an executor.
        """
        if is_coroutine_function(func):
            return func
        else:
            return run_sync(func)

    async def handle_request(self, request: Request) -> Response:
        async with self.request_context(request) as request_context:
            try:
                return await self.full_dispatch_request(request_context)
            except trio.Cancelled:
                raise  # Cancelled should be handled by serving code.
            except (Exception, trio.MultiError) as error:
                return await self.handle_exception(error)

    async def full_dispatch_request(
        self, request_context: Optional[RequestContext] = None
    ) -> Response:
        """Adds pre and post processing to the request dispatching.

        Arguments:
            request_context: The request context, optional as Flask
                omits this argument.
        """
        await self.try_trigger_before_first_request_functions()
        await request_started.send(self)
        try:
            result = await self.preprocess_request(request_context)
            if result is None:
                result = await self.dispatch_request(request_context)
        except (Exception, trio.MultiError) as error:
            result = await self.handle_user_exception(error)
        return await self.finalize_request(result, request_context)

    async def handle_user_exception(self, error: Union[Exception, trio.MultiError]) -> Response:
        if isinstance(error, trio.MultiError):
            for exception in error.exceptions:
                try:
                    return await self.handle_user_exception(exception)
                except Exception:
                    pass  # No handler for this error
            # Not found a single handler, re-raise the error
            raise error
        else:
            return await super().handle_user_exception(error)

    async def handle_websocket(self, websocket: Websocket) -> Optional[Response]:
        async with self.websocket_context(websocket) as websocket_context:
            try:
                return await self.full_dispatch_websocket(websocket_context)
            except trio.Cancelled:
                raise  # Cancelled should be handled by serving code.
            except (Exception, trio.MultiError) as error:
                return await self.handle_websocket_exception(error)

    async def full_dispatch_websocket(
        self, websocket_context: Optional[WebsocketContext] = None
    ) -> Optional[Response]:
        """Adds pre and post processing to the websocket dispatching.

        Arguments:
            websocket_context: The websocket context, optional to match
                the Flask convention.
        """
        await self.try_trigger_before_first_request_functions()
        await websocket_started.send(self)
        try:
            result = await self.preprocess_websocket(websocket_context)
            if result is None:
                result = await self.dispatch_websocket(websocket_context)
        except (Exception, trio.MultiError) as error:
            result = await self.handle_user_exception(error)
        return await self.finalize_websocket(result, websocket_context)
