from pathlib import Path

import pytest
from py._path.local import LocalPath
from quart import abort, Quart, ResponseReturnValue, send_file, websocket
from quart.testing import WebsocketResponse

from quart_trio import QuartTrio


@pytest.fixture
def app() -> Quart:
    app = QuartTrio(__name__)

    @app.route("/")
    async def index() -> ResponseReturnValue:
        return "index"

    @app.websocket("/ws/")
    async def ws() -> None:
        # async for message in websocket:
        while True:
            message = await websocket.receive()
            await websocket.send(message)

    @app.websocket("/ws/abort/")
    async def ws_abort() -> None:
        abort(401)

    return app


@pytest.mark.trio
async def test_index(app: Quart) -> None:
    test_client = app.test_client()
    response = await test_client.get("/")
    assert response.status_code == 200
    assert b"index" in (await response.get_data())  # type: ignore


@pytest.mark.trio
async def test_websocket(app: Quart) -> None:
    test_client = app.test_client()
    data = b"bob"
    async with test_client.websocket("/ws/") as test_websocket:
        await test_websocket.send(data)
        result = await test_websocket.receive()
    assert result == data  # type: ignore


@pytest.mark.trio
async def test_websocket_abort(app: Quart) -> None:
    test_client = app.test_client()
    try:
        async with test_client.websocket("/ws/abort/") as test_websocket:
            await test_websocket.receive()
    except WebsocketResponse as error:
        assert error.response.status_code == 401


@pytest.mark.trio
async def test_send_file_path(tmpdir: LocalPath) -> None:
    app = QuartTrio(__name__)
    file_ = tmpdir.join("send.img")
    file_.write("something")
    async with app.app_context():
        response = await send_file(Path(file_.realpath()))
    assert (await response.get_data(raw=True)) == file_.read_binary()
