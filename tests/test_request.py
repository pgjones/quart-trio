import pytest
import trio
from quart.wrappers.base import ClientDisconnectedError
from werkzeug.exceptions import RequestEntityTooLarge

from quart_trio.wrappers.request import TrioBody


@pytest.mark.trio
async def test_body_exceeds_max_content_length() -> None:
    max_content_length = 5
    body = TrioBody(None, max_content_length)
    await body.put(b" " * (max_content_length + 1))
    body.set_complete()
    with pytest.raises(RequestEntityTooLarge):
        await body


@pytest.mark.trio
async def test_body_streaming() -> None:
    body = TrioBody(None, None)

    async def produce() -> None:
        await body.put(b"first")
        await body.put(b"second")
        body.set_complete()

    async with trio.open_nursery() as nursery:
        nursery.start_soon(produce)
        data = b"".join([chunk async for chunk in body])
    assert data == b"firstsecond"


@pytest.mark.trio
async def test_body_disconnect() -> None:
    body = TrioBody(None, None)
    body.disconnect()
    with pytest.raises(ClientDisconnectedError):
        await body.get()
