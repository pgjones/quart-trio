from __future__ import annotations

from typing import Type

from quart.testing.client import QuartClient
from quart.typing import TestHTTPConnectionProtocol, TestWebsocketConnectionProtocol

from .connections import TestHTTPConnection, TestWebsocketConnection


class TrioClient(QuartClient):
    http_connection_class: Type[TestHTTPConnectionProtocol] = TestHTTPConnection
    websocket_connection_class: Type[TestWebsocketConnectionProtocol] = TestWebsocketConnection
