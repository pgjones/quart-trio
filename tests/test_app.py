from typing import NoReturn

import pytest
from exceptiongroup import BaseExceptionGroup
from quart import ResponseReturnValue
from quart.testing import WebsocketResponseError

from quart_trio import QuartTrio


@pytest.fixture(name="error_app", scope="function")
def _error_app() -> QuartTrio:
    app = QuartTrio(__name__)

    @app.route("/")
    async def index() -> NoReturn:
        raise BaseExceptionGroup(
            "msg1", [ValueError(), BaseExceptionGroup("msg2", [TypeError(), ValueError()])]
        )

    @app.websocket("/ws/")
    async def ws() -> NoReturn:
        raise BaseExceptionGroup(
            "msg3", [ValueError(), BaseExceptionGroup("msg4", [TypeError(), ValueError()])]
        )

    return app


@pytest.mark.trio
async def test_exception_group_handling(error_app: QuartTrio) -> None:
    @error_app.errorhandler(TypeError)
    async def handler(_: Exception) -> ResponseReturnValue:
        return "", 201

    test_client = error_app.test_client()
    response = await test_client.get("/")
    assert response.status_code == 201


@pytest.mark.trio
async def test_websocket_exception_group_handling(error_app: QuartTrio) -> None:
    @error_app.errorhandler(TypeError)
    async def handler(_: Exception) -> ResponseReturnValue:
        return "", 201

    test_client = error_app.test_client()
    try:
        async with test_client.websocket("/ws/") as test_websocket:
            await test_websocket.receive()
    except WebsocketResponseError as error:
        assert error.response.status_code == 201


@pytest.mark.trio
async def test_exception_group_unhandled(error_app: QuartTrio) -> None:
    test_client = error_app.test_client()
    response = await test_client.get("/")
    assert response.status_code == 500


@pytest.mark.trio
async def test_websocket_exception_group_unhandled(error_app: QuartTrio) -> None:
    test_client = error_app.test_client()
    try:
        async with test_client.websocket("/ws/") as test_websocket:
            await test_websocket.receive()
    except WebsocketResponseError as error:
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
