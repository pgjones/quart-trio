from functools import partial
from typing import cast, Optional, TYPE_CHECKING, Union
from urllib.parse import urlparse

import trio
from exceptiongroup import BaseExceptionGroup
from hypercorn.typing import (
    ASGIReceiveCallable,
    ASGISendCallable,
    LifespanScope,
    LifespanShutdownCompleteEvent,
    LifespanShutdownFailedEvent,
    LifespanStartupCompleteEvent,
    LifespanStartupFailedEvent,
    WebsocketScope,
)
from quart.asgi import ASGIHTTPConnection, ASGIWebsocketConnection
from quart.signals import websocket_received
from quart.wrappers import Request, Response, Websocket  # noqa: F401
from werkzeug.datastructures import Headers

if TYPE_CHECKING:
    from quart_trio import QuartTrio  # noqa: F401


class TrioASGIHTTPConnection(ASGIHTTPConnection):
    async def __call__(self, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        request = self._create_request_from_scope(send)
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.handle_messages, nursery, request, receive)
            nursery.start_soon(self.handle_request, nursery, request, send)

    async def handle_messages(  # type: ignore
        self, nursery: trio.Nursery, request: Request, receive: ASGIReceiveCallable
    ) -> None:
        await super().handle_messages(request, receive)
        nursery.cancel_scope.cancel()

    async def handle_request(  # type: ignore
        self, nursery: trio.Nursery, request: Request, send: ASGISendCallable
    ) -> None:
        response = await self.app.handle_request(request)
        if isinstance(response, Response) and response.timeout != Ellipsis:
            timeout = cast(Optional[float], response.timeout)
        else:
            timeout = self.app.config["RESPONSE_TIMEOUT"]

        if timeout is not None:
            with trio.move_on_after(timeout):
                await self._send_response(send, response)
        else:
            await self._send_response(send, response)
        nursery.cancel_scope.cancel()


class TrioASGIWebsocketConnection(ASGIWebsocketConnection):
    def __init__(self, app: "QuartTrio", scope: WebsocketScope) -> None:
        self.app = app
        self.scope = scope
        self._accepted = False
        self._closed = False
        self.send_channel, self.receive_channel = trio.open_memory_channel[Union[bytes, str]](10)

    async def __call__(self, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        websocket = self._create_websocket_from_scope(send)
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.handle_messages, nursery, receive)
            nursery.start_soon(self.handle_websocket, nursery, websocket, send)

    async def handle_messages(  # type: ignore
        self, nursery: trio.Nursery, receive: ASGIReceiveCallable
    ) -> None:
        while True:
            event = await receive()
            if event["type"] == "websocket.receive":
                message = event.get("bytes") or event["text"]
                await websocket_received.send_async(message, _sync_wrapper=self.app.ensure_async)
                await self.send_channel.send(message)
            elif event["type"] == "websocket.disconnect":
                break
        nursery.cancel_scope.cancel()

    def _create_websocket_from_scope(self, send: ASGISendCallable) -> Websocket:
        headers = Headers()
        headers["Remote-Addr"] = (self.scope.get("client") or ["<local>"])[0]
        for name, value in self.scope["headers"]:
            headers.add(name.decode("latin1").title(), value.decode("latin1"))

        path = self.scope["path"]
        path = path if path[0] == "/" else urlparse(path).path
        root_path = self.scope.get("root_path", "")
        if root_path != "":
            try:
                path = path.split(root_path, 1)[1]
                path = " " if path == "" else path
            except IndexError:
                path = " "  # Invalid in paths, hence will result in 404

        return self.app.websocket_class(
            path,
            self.scope["query_string"],
            self.scope["scheme"],
            headers,
            self.scope.get("root_path", ""),
            self.scope.get("http_version", "1.1"),
            list(self.scope.get("subprotocols", [])),
            self.receive_channel.receive,
            partial(self.send_data, send),
            partial(self.accept_connection, send),
            partial(self.close_connection, send),
            scope=self.scope,
        )

    async def handle_websocket(  # type: ignore
        self, nursery: trio.Nursery, websocket: Websocket, send: ASGISendCallable
    ) -> None:
        await super().handle_websocket(websocket, send)
        nursery.cancel_scope.cancel()


class TrioASGILifespan:
    def __init__(self, app: "QuartTrio", scope: LifespanScope) -> None:
        self.app = app

    async def __call__(self, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        async with trio.open_nursery() as nursery:
            self.app.nursery = nursery
            while True:
                event = await receive()
                if event["type"] == "lifespan.startup":
                    try:
                        await self.app.startup()
                    except (Exception, BaseExceptionGroup) as error:
                        await send(
                            cast(
                                LifespanStartupFailedEvent,
                                {"type": "lifespan.startup.failed", "message": str(error)},
                            ),
                        )
                    else:
                        await send(
                            cast(
                                LifespanStartupCompleteEvent, {"type": "lifespan.startup.complete"}
                            )
                        )
                elif event["type"] == "lifespan.shutdown":
                    try:
                        await self.app.shutdown()
                    except (Exception, BaseExceptionGroup) as error:
                        await send(
                            cast(
                                LifespanShutdownFailedEvent,
                                {"type": "lifespan.shutdown.failed", "message": str(error)},
                            ),
                        )
                    else:
                        await send(
                            cast(
                                LifespanShutdownCompleteEvent,
                                {"type": "lifespan.shutdown.complete"},
                            ),
                        )
                    break
