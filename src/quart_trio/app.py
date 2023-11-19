import sys
import warnings
from typing import Any, Awaitable, Callable, Coroutine, Optional, TypeVar, Union

import trio
from exceptiongroup import BaseExceptionGroup
from hypercorn.config import Config as HyperConfig
from hypercorn.trio import serve
from quart import Quart, request_started, websocket_started
from quart.ctx import RequestContext, WebsocketContext
from quart.signals import got_serving_exception
from quart.typing import FilePath, ResponseReturnValue
from quart.utils import file_path_to_path
from quart.wrappers import Request, Response, Websocket
from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import Response as WerkzeugResponse

from .asgi import TrioASGIHTTPConnection, TrioASGILifespan, TrioASGIWebsocketConnection
from .testing import TrioClient, TrioTestApp
from .utils import run_sync
from .wrappers import TrioRequest, TrioResponse, TrioWebsocket

try:
    from typing import ParamSpec
except ImportError:
    from typing_extensions import ParamSpec  # type: ignore

T = TypeVar("T")
P = ParamSpec("P")


class QuartTrio(Quart):
    nursery: trio.Nursery
    asgi_http_class = TrioASGIHTTPConnection
    asgi_lifespan_class = TrioASGILifespan
    asgi_websocket_class = TrioASGIWebsocketConnection
    event_class = trio.Event  # type: ignore
    lock_class = trio.Lock  # type: ignore
    request_class = TrioRequest
    response_class = TrioResponse
    test_app_class = TrioTestApp
    test_client_class = TrioClient  # type: ignore
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
        print(f"Running on {scheme}://{host}:{port} (CTRL + C to quit)")  # noqa: T201

        trio.run(self.run_task, host, port, debug, ca_certs, certfile, keyfile)  # type: ignore

    def run_task(
        self,
        host: str = "127.0.0.1",
        port: int = 5000,
        debug: Optional[bool] = None,
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
        config.accesslog = "-"
        config.bind = [f"{host}:{port}"]
        config.ca_certs = ca_certs
        config.certfile = certfile
        if debug is not None:
            config.debug = debug
        config.errorlog = config.accesslog
        config.keyfile = keyfile

        return serve(self, config, shutdown_trigger=shutdown_trigger)

    def sync_to_async(self, func: Callable[P, T]) -> Callable[P, Awaitable[T]]:
        """Return a async function that will run the synchronous function *func*.

        This can be used as so,::

            result = await app.sync_to_async(func)(*args, **kwargs)

        Override this method to change how the app converts sync code
        to be asynchronously callable.
        """
        return run_sync(func)

    async def handle_request(self, request: Request) -> Union[Response, WerkzeugResponse]:
        async with self.request_context(request) as request_context:
            try:
                return await self.full_dispatch_request(request_context)
            except trio.Cancelled:
                raise  # Cancelled should be handled by serving code.
            except BaseExceptionGroup as error:
                filtered_error, _ = error.split(trio.Cancelled)
                if filtered_error is not None:
                    raise filtered_error

                return await self.handle_exception(error)  # type: ignore
            except Exception as error:
                return await self.handle_exception(error)
            finally:
                if request.scope.get("_quart._preserve_context", False):
                    self._preserved_context = request_context.copy()

    async def full_dispatch_request(
        self, request_context: Optional[RequestContext] = None
    ) -> Union[Response, WerkzeugResponse]:
        """Adds pre and post processing to the request dispatching.

        Arguments:
            request_context: The request context, optional as Flask
                omits this argument.
        """
        try:
            await request_started.send_async(self, _sync_wrapper=self.ensure_async)

            result: ResponseReturnValue | HTTPException | None
            result = await self.preprocess_request(request_context)
            if result is None:
                result = await self.dispatch_request(request_context)
        except (Exception, BaseExceptionGroup) as error:
            result = await self.handle_user_exception(error)
        return await self.finalize_request(result, request_context)

    async def handle_user_exception(
        self, error: Union[Exception, BaseExceptionGroup]
    ) -> Union[HTTPException, ResponseReturnValue]:
        if isinstance(error, BaseExceptionGroup):
            for exception in error.exceptions:
                try:
                    return await self.handle_user_exception(exception)
                except Exception:
                    pass  # No handler for this error
            # Not found a single handler, re-raise the error
            raise error
        else:
            return await super().handle_user_exception(error)

    async def handle_websocket(
        self, websocket: Websocket
    ) -> Optional[Union[Response, WerkzeugResponse]]:
        async with self.websocket_context(websocket) as websocket_context:
            try:
                return await self.full_dispatch_websocket(websocket_context)
            except trio.Cancelled:
                raise  # Cancelled should be handled by serving code.
            except BaseExceptionGroup as error:
                filtered_error, _ = error.split(trio.Cancelled)
                if filtered_error is not None:
                    raise filtered_error

                return await self.handle_websocket_exception(error)  # type: ignore
            except Exception as error:
                return await self.handle_websocket_exception(error)
            finally:
                if websocket.scope.get("_quart._preserve_context", False):
                    self._preserved_context = websocket_context.copy()

    async def full_dispatch_websocket(
        self, websocket_context: Optional[WebsocketContext] = None
    ) -> Optional[Union[Response, WerkzeugResponse]]:
        """Adds pre and post processing to the websocket dispatching.

        Arguments:
            websocket_context: The websocket context, optional to match
                the Flask convention.
        """
        try:
            await websocket_started.send_async(self, _sync_wrapper=self.ensure_async)

            result: ResponseReturnValue | HTTPException | None
            result = await self.preprocess_websocket(websocket_context)
            if result is None:
                result = await self.dispatch_websocket(websocket_context)
        except (Exception, BaseExceptionGroup) as error:
            result = await self.handle_user_exception(error)
        return await self.finalize_websocket(result, websocket_context)

    async def open_instance_resource(
        self, path: FilePath, mode: str = "rb"
    ) -> trio._file_io.AsyncIOWrapper:  # type: ignore
        """Open a file for reading.

        Use as

        .. code-block:: python

            async with await app.open_instance_resource(path) as file_:
                await file_.read()
        """
        return await trio.open_file(self.instance_path / file_path_to_path(path), mode)

    async def open_resource(
        self, path: FilePath, mode: str = "rb"
    ) -> trio._file_io.AsyncIOWrapper:  # type: ignore
        """Open a file for reading.

        Use as

        .. code-block:: python

            async with await app.open_resource(path) as file_:
                await file_.read()
        """
        if mode not in {"r", "rb"}:
            raise ValueError("Files can only be opened for reading")

        return await trio.open_file(self.root_path / file_path_to_path(path), mode)

    def add_background_task(self, func: Callable, *args: Any, **kwargs: Any) -> None:
        async def _wrapper() -> None:
            try:
                async with self.app_context():
                    await self.ensure_async(func)(*args, **kwargs)
            except (BaseExceptionGroup, Exception) as error:
                await self.handle_background_exception(error)  # type: ignore

        self.nursery.start_soon(_wrapper)

    async def shutdown(self) -> None:
        if self.config["BACKGROUND_TASK_SHUTDOWN_TIMEOUT"] is not None:
            self.nursery.cancel_scope.deadline = (
                trio.current_time() + self.config["BACKGROUND_TASK_SHUTDOWN_TIMEOUT"]
            )
        else:
            self.nursery.cancel_scope.cancel()

        try:
            async with self.app_context():
                for func in self.after_serving_funcs:
                    await self.ensure_async(func)()
                for gen in self.while_serving_gens:
                    try:
                        await gen.__anext__()
                    except StopAsyncIteration:
                        pass
                    else:
                        raise RuntimeError("While serving generator didn't terminate")
        except Exception as error:
            await got_serving_exception.send_async(
                self, _sync_wrapper=self.ensure_async, exception=error
            )
            self.log_exception(sys.exc_info())
            raise
