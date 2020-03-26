from functools import partial
from typing import Callable, cast, Optional, TYPE_CHECKING

import trio
from quart.asgi import ASGIHTTPConnection, ASGIWebsocketConnection
from quart.wrappers import Request, Response, sentinel, Websocket  # noqa: F401
from werkzeug.datastructures import Headers

if TYPE_CHECKING:
    from quart import Quart  # noqa: F401


class TrioASGIHTTPConnection(ASGIHTTPConnection):
    async def __call__(self, receive: Callable, send: Callable) -> None:
        request = self._create_request_from_scope(send)
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.handle_messages, nursery, request, receive)
            nursery.start_soon(self.handle_request, nursery, request, send)

    async def handle_messages(  # type: ignore
        self, nursery: trio._core._run.Nursery, request: Request, receive: Callable
    ) -> None:
        await super().handle_messages(request, receive)
        nursery.cancel_scope.cancel()

    async def handle_request(  # type: ignore
        self, nursery: trio._core._run.Nursery, request: Request, send: Callable
    ) -> None:
        response = await self.app.handle_request(request)
        if response.timeout != sentinel:
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
    def __init__(self, app: "Quart", scope: dict) -> None:
        super().__init__(app, scope)
        self.send_channel, self.receive_channel = trio.open_memory_channel(10)

    async def __call__(self, receive: Callable, send: Callable) -> None:
        websocket = self._create_websocket_from_scope(send)
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.handle_messages, nursery, receive)
            nursery.start_soon(self.handle_websocket, nursery, websocket, send)

    async def handle_messages(  # type: ignore
        self, nursery: trio._core._run.Nursery, receive: Callable
    ) -> None:
        while True:
            event = await receive()
            if event["type"] == "websocket.receive":
                await self.send_channel.send(event.get("bytes") or event["text"])
            elif event["type"] == "websocket.disconnect":
                break
        nursery.cancel_scope.cancel()

    def _create_websocket_from_scope(self, send: Callable) -> Websocket:
        headers = Headers()
        headers["Remote-Addr"] = (self.scope.get("client") or ["<local>"])[0]
        for name, value in self.scope["headers"]:
            headers.add(name.decode().title(), value.decode())

        return self.app.websocket_class(
            self.scope["path"],
            self.scope["query_string"],
            self.scope["scheme"],
            headers,
            self.scope.get("root_path", ""),
            self.scope.get("http_version", "1.1"),
            self.scope.get("subprotocols", []),
            self.receive_channel.receive,
            partial(self.send_data, send),
            partial(self.accept_connection, send),
        )

    async def handle_websocket(  # type: ignore
        self, nursery: trio._core._run.Nursery, websocket: Websocket, send: Callable
    ) -> None:
        await super().handle_websocket(websocket, send)
        nursery.cancel_scope.cancel()


class TrioASGILifespan:
    def __init__(self, app: "Quart", scope: dict) -> None:
        self.app = app

    async def __call__(self, receive: Callable, send: Callable) -> None:
        async with trio.open_nursery() as nursery:
            self.app.nursery = nursery  # type: ignore
            while True:
                event = await receive()
                if event["type"] == "lifespan.startup":
                    try:
                        await self.app.startup()
                    except Exception as error:
                        await send({"type": "lifespan.startup.failed", "message": str(error)})
                    else:
                        await send({"type": "lifespan.startup.complete"})
                elif event["type"] == "lifespan.shutdown":
                    try:
                        await self.app.shutdown()
                    except Exception as error:
                        await send({"type": "lifespan.shutdown.failed", "message": str(error)})
                    else:
                        await send({"type": "lifespan.shutdown.complete"})
                    break
