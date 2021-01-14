import pytest
import trio
from hypercorn.typing import WebsocketScope

from quart_trio.app import QuartTrio
from quart_trio.asgi import TrioASGIWebsocketConnection


@pytest.mark.trio
async def test_websocket_complete_on_disconnect() -> None:
    scope: WebsocketScope = {
        "type": "websocket",
        "asgi": {},
        "http_version": "1.1",
        "scheme": "wss",
        "path": "ws://quart/path",
        "raw_path": b"/",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"quart")],
        "client": ("127.0.0.1", 80),
        "server": None,
        "subprotocols": [],
        "extensions": {"websocket.http.response": {}},
    }
    connection = TrioASGIWebsocketConnection(QuartTrio(__name__), scope)
    send_channel, receive_channel = trio.open_memory_channel(0)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(connection.handle_messages, nursery, receive_channel.receive)
        await send_channel.send({"type": "websocket.disconnect"})
    assert nursery.cancel_scope.cancelled_caught
