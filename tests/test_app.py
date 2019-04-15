from typing import NoReturn

import pytest
import trio
from quart.testing import WebsocketResponse

from quart_trio import QuartTrio


@pytest.mark.trio
async def test_multi_error_handling() -> None:
    app = QuartTrio(__name__)

    @app.route("/")
    async def index() -> NoReturn:
        raise trio.MultiError([ValueError(), TypeError()])

    test_client = app.test_client()
    response = await test_client.get("/")
    assert response.status_code == 500


@pytest.mark.trio
async def test_websocket_multi_error_handling() -> None:
    app = QuartTrio(__name__)

    @app.websocket("/")
    async def index() -> NoReturn:
        raise trio.MultiError([ValueError(), TypeError()])

    test_client = app.test_client()
    try:
        async with test_client.websocket("/") as test_websocket:
            await test_websocket.receive()
    except WebsocketResponse as error:
        assert error.response.status_code == 500
