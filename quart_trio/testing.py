from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Union

import trio
from quart.datastructures import CIMultiDict
from quart.exceptions import BadRequest
from quart.testing import make_test_headers_path_and_query_string, QuartClient, WebsocketResponse
from quart.wrappers import Request, Response, Websocket


class _TestingWebsocket:
    def __init__(
        self,
        server_send: trio._channel.MemorySendChannel,
        client_receive: trio._channel.MemoryReceiveChannel,
    ) -> None:
        self.server_send = server_send
        self.client_receive = client_receive
        self.accepted = False

    async def receive(self) -> bytes:
        return await self.client_receive.receive()

    async def send(self, data: bytes) -> None:
        await self.server_send.send(data)

    async def accept(self) -> None:
        self.accepted = True


class TrioQuartClient(QuartClient):
    async def _handle_request(self, request: Request) -> Response:
        return await self.app.handle_request(request)

    @asynccontextmanager
    async def websocket(
        self,
        path: str,
        *,
        headers: Optional[Union[dict, CIMultiDict]] = None,
        query_string: Optional[dict] = None,
        scheme: str = "http",
    ) -> AsyncGenerator[_TestingWebsocket, None]:
        headers, path, query_string_bytes = make_test_headers_path_and_query_string(
            self.app, path, headers, query_string
        )
        server_send, server_receive = trio.open_memory_channel(10)
        client_send, client_receive = trio.open_memory_channel(10)
        websocket_client = _TestingWebsocket(server_send, client_receive)

        websocket = self.app.websocket_class(
            path,
            query_string_bytes,
            scheme,
            headers,
            server_receive.receive,
            client_send.send,
            websocket_client.accept,
        )
        adapter = self.app.create_url_adapter(websocket)
        url_rule, _ = adapter.match()
        if not url_rule.is_websocket:
            raise BadRequest()

        async with trio.open_nursery() as nursery:
            nursery.start_soon(self._handle_websocket, websocket)
            try:
                yield websocket_client
            finally:
                nursery.cancel_scope.cancel()

    async def _handle_websocket(self, websocket: Websocket) -> None:
        response = await self.app.handle_websocket(websocket)
        if response is not None:
            raise WebsocketResponse(response)
