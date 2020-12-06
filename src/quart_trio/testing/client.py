from __future__ import annotations

from quart.testing.client import QuartClient

from .connections import TestHTTPConnection, TestWebsocketConnection


class TrioClient(QuartClient):
    http_connection_class = TestHTTPConnection  # type: ignore
    websocket_connection_class = TestWebsocketConnection  # type: ignore
