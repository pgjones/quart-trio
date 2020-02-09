import threading
from typing import Generator

import pytest
from quart import request, ResponseReturnValue

from quart_trio import QuartTrio


@pytest.fixture(name="app")
def _app() -> QuartTrio:
    app = QuartTrio(__name__)

    @app.route("/", methods=["GET", "POST"])
    def index() -> ResponseReturnValue:
        return request.method

    @app.route("/gen")
    def gen() -> ResponseReturnValue:
        def _gen() -> Generator[bytes, None, None]:
            yield b"%d" % threading.current_thread().ident
            for _ in range(2):
                yield b"b"

        return _gen(), 200

    return app


@pytest.mark.trio
async def test_sync_request_context(app: QuartTrio) -> None:
    test_client = app.test_client()
    response = await test_client.get("/")
    assert b"GET" in (await response.get_data())  # type: ignore
    response = await test_client.post("/")
    assert b"POST" in (await response.get_data())  # type: ignore


@pytest.mark.trio
async def test_sync_generator(app: QuartTrio) -> None:
    test_client = app.test_client()
    response = await test_client.get("/gen")
    result = await response.get_data()
    assert result[-2:] == b"bb"  # type: ignore
    assert int(result[:-2]) != threading.current_thread().ident
