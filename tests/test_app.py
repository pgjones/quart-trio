from typing import NoReturn

import pytest
import trio
from quart import ResponseReturnValue
from quart.testing import WebsocketResponse

from quart_trio import QuartTrio


@pytest.fixture(name="error_app", scope="function")
def _error_app() -> QuartTrio:
    app = QuartTrio(__name__)

    @app.route("/")
    async def index() -> NoReturn:
        raise trio.MultiError([ValueError(), trio.MultiError([TypeError(), ValueError()])])

    @app.websocket("/ws/")
    async def ws() -> NoReturn:
        raise trio.MultiError([ValueError(), trio.MultiError([TypeError(), ValueError()])])

    return app


@pytest.mark.trio
async def test_multi_error_handling(error_app: QuartTrio) -> None:
    @error_app.errorhandler(TypeError)
    async def handler(_: Exception) -> ResponseReturnValue:
        return "", 201

    test_client = error_app.test_client()
    response = await test_client.get("/")
    assert response.status_code == 201


@pytest.mark.trio
async def test_websocket_multi_error_handling(error_app: QuartTrio) -> None:
    @error_app.errorhandler(TypeError)
    async def handler(_: Exception) -> ResponseReturnValue:
        return "", 201

    test_client = error_app.test_client()
    try:
        async with test_client.websocket("/ws/") as test_websocket:
            await test_websocket.receive()
    except WebsocketResponse as error:
        assert error.response.status_code == 201


@pytest.mark.trio
async def test_multi_error_unhandled(error_app: QuartTrio) -> None:
    test_client = error_app.test_client()
    response = await test_client.get("/")
    assert response.status_code == 500


@pytest.mark.trio
async def test_websocket_multi_error_unhandled(error_app: QuartTrio) -> None:
    test_client = error_app.test_client()
    try:
        async with test_client.websocket("/ws/") as test_websocket:
            await test_websocket.receive()
    except WebsocketResponse as error:
        assert error.response.status_code == 500


@pytest.mark.trio
async def test_test_app() -> None:
    startup = False
    shutdown = False

    app = QuartTrio(__name__)

    @app.before_serving
    async def before() -> None:
        nonlocal startup
        startup = True

    @app.after_serving
    async def after() -> None:
        nonlocal shutdown
        shutdown = True

    @app.route("/")
    async def index() -> str:
        return ""

    async with app.test_app() as test_app:
        assert startup
        assert app.nursery is not None
        test_client = test_app.test_client()
        await test_client.get("/")
        assert not shutdown
    assert shutdown
