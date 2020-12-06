from __future__ import annotations

from types import TracebackType
from typing import Any, AnyStr, Awaitable, List, Optional, Tuple

import trio
from quart.app import Quart
from quart.json import dumps, loads
from quart.testing.connections import HTTPDisconnect, WebsocketDisconnect, WebsocketResponse
from quart.utils import decode_headers
from quart.wrappers import Response
from werkzeug.datastructures import Headers


class TestHTTPConnection:
    def __init__(self, app: Quart, scope: dict, _preserve_context: bool = False) -> None:
        self.app = app
        self.headers: Optional[Headers] = None
        self.push_promises: List[Tuple[str, Headers]] = []
        self.response_data = bytearray()
        self.scope = scope
        self.status_code: Optional[int] = None
        self._preserve_context = _preserve_context
        self._server_send, self._server_receive = trio.open_memory_channel(10)
        self._client_send, self._client_receive = trio.open_memory_channel(10)

    async def send(self, data: bytes) -> None:
        await self._server_send.send({"type": "http.request", "body": data, "more_body": True})

    async def send_complete(self) -> None:
        await self._server_send.send({"type": "http.request", "body": b"", "more_body": False})

    async def receive(self) -> bytes:
        data = await self._client_receive.receive()
        if isinstance(data, Exception):
            raise data
        else:
            return data

    async def close(self) -> None:
        await self._server_send.send({"type": "http.disconnect"})
        await self._server_send.aclose()

    async def __aenter__(self) -> "TestHTTPConnection":
        self._nursery_manager = trio.open_nursery()
        nursery = await self._nursery_manager.__aenter__()
        nursery.start_soon(self.app, self.scope, self._asgi_receive, self._asgi_send)
        return self

    async def __aexit__(self, exc_type: type, exc_value: BaseException, tb: TracebackType) -> None:
        if exc_type is not None:
            await self.close()
        await self._nursery_manager.__aexit__(exc_type, exc_value, tb)
        try:
            async with self._client_receive:
                async for data in self._client_receive:
                    if isinstance(data, bytes):
                        self.response_data.extend(data)
                    elif not isinstance(data, HTTPDisconnect):
                        raise data
        except trio.ClosedResourceError:
            pass

    async def as_response(self) -> Response:
        try:
            async with self._client_receive:
                async for data in self._client_receive:
                    if isinstance(data, bytes):
                        self.response_data.extend(data)
        except trio.ClosedResourceError:
            pass
        return self.app.response_class(bytes(self.response_data), self.status_code, self.headers)

    async def _asgi_receive(self) -> dict:
        return await self._server_receive.receive()

    async def _asgi_send(self, message: dict) -> None:
        if message["type"] == "http.response.start":
            self.headers = decode_headers(message["headers"])
            self.status_code = message["status"]
        elif message["type"] == "http.response.body":
            await self._client_send.send(message["body"])
            if not message.get("more_body", False):
                await self._client_send.aclose()
        elif message["type"] == "http.response.push":
            self.push_promises.append((message["path"], decode_headers(message["headers"])))
        elif message["type"] == "http.disconnect":
            await self._client_send.send(HTTPDisconnect())
            await self._client_send.aclose()


class TestWebsocketConnection:
    def __init__(self, app: Quart, scope: dict) -> None:
        self.accepted = False
        self.app = app
        self.headers: Optional[Headers] = None
        self.response_data = bytearray()
        self.scope = scope
        self.status_code: Optional[int] = None
        self._server_send, self._server_receive = trio.open_memory_channel(10)
        self._client_send, self._client_receive = trio.open_memory_channel(10)
        self._task: Awaitable[None] = None

    async def __aenter__(self) -> "TestWebsocketConnection":
        self._nursery_manager = trio.open_nursery()
        nursery = await self._nursery_manager.__aenter__()
        nursery.start_soon(self.app, self.scope, self._asgi_receive, self._asgi_send)
        return self

    async def __aexit__(self, exc_type: type, exc_value: BaseException, tb: TracebackType) -> None:
        await self.close()
        await self._nursery_manager.__aexit__(exc_type, exc_value, tb)

    async def receive(self) -> AnyStr:
        data = await self._client_receive.receive()
        if isinstance(data, Exception):
            raise data
        else:
            return data

    async def send(self, data: AnyStr) -> None:
        if isinstance(data, str):
            await self._server_send.send({"type": "websocket.receive", "text": data})
        else:
            await self._server_send.send({"type": "websocket.receive", "bytes": data})

    async def receive_json(self) -> Any:
        data = await self.receive()
        return loads(data)

    async def send_json(self, data: Any) -> None:
        raw = dumps(data)
        await self.send(raw)

    async def close(self) -> None:
        await self._server_send.send({"type": "websocket.disconnect"})
        await self._server_send.aclose()

    async def _asgi_receive(self) -> dict:
        return await self._server_receive.receive()

    async def _asgi_send(self, message: dict) -> None:
        if message["type"] == "websocket.accept":
            self.accepted = True
        elif message["type"] == "websocket.send":
            await self._client_send.send(message.get("bytes") or message.get("text"))
        elif message["type"] == "websocket.http.response.start":
            self.headers = decode_headers(message["headers"])
            self.status_code = message["status"]
        elif message["type"] == "websocket.http.response.body":
            self.response_data.extend(message["body"])
            if not message.get("more_body", False):
                await self._client_send.send(
                    WebsocketResponse(
                        self.app.response_class(
                            bytes(self.response_data), self.status_code, self.headers
                        )
                    )
                )
        elif message["type"] == "websocket.close":
            await self._client_send.send(WebsocketDisconnect(message.get("code", 1000)))
            await self._client_send.aclose()
