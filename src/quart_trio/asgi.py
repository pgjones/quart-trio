from typing import cast, Optional, TYPE_CHECKING

import trio
from hypercorn.typing import (
    ASGIReceiveCallable,
    ASGISendCallable,
    LifespanScope,
    LifespanShutdownCompleteEvent,
    LifespanShutdownFailedEvent,
    LifespanStartupCompleteEvent,
    LifespanStartupFailedEvent,
)
from quart.asgi import _convert_os_error, ASGIHTTPConnection, ASGIWebsocketConnection
from quart.signals import websocket_received
from quart.wrappers import Request, Response, Websocket  # noqa: F401

if TYPE_CHECKING:
    from quart_trio import QuartTrio  # noqa: F401


class TrioASGIHTTPConnection(ASGIHTTPConnection):
    async def __call__(self, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        send = _convert_os_error(send)
        request = self._create_request_from_scope(send)
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.handle_messages, nursery, request, receive)
            nursery.start_soon(self.handle_request, nursery, request, send)

    async def handle_messages(  # type: ignore
        self, nursery: trio.Nursery, request: Request, receive: ASGIReceiveCallable
    ) -> None:
        while True:
            message = await receive()
            if message["type"] == "http.request":
                await request.body.put(message.get("body", b""))
                if not message.get("more_body", False):
                    request.body.set_complete()
            elif message["type"] == "http.disconnect":
                self._disconnected = True
                request.body.disconnect()
                nursery.cancel_scope.cancel()
                return

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
    async def __call__(self, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        send = _convert_os_error(send)
        websocket = self._create_websocket_from_scope(send)
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.handle_messages, nursery, websocket, receive)
            nursery.start_soon(self.handle_websocket, nursery, websocket, send)

    async def handle_messages(  # type: ignore
        self, nursery: trio.Nursery, websocket: Websocket, receive: ASGIReceiveCallable
    ) -> None:
        while True:
            event = await receive()
            if event["type"] == "websocket.receive":
                message = event.get("bytes") or event["text"]
                await websocket_received.send_async(
                    message, _sync_wrapper=self.app.ensure_async  # type: ignore
                )
                await websocket.buffer.put(message)
            elif event["type"] == "websocket.disconnect":
                self._disconnected = True
                websocket.buffer.disconnect()
                break
        nursery.cancel_scope.cancel()

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
