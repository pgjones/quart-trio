import pytest
from quart.exceptions import RequestEntityTooLarge

from quart_trio.request import TrioBody


@pytest.mark.trio
async def test_body_exceeds_max_content_length() -> None:
    max_content_length = 5
    body = TrioBody(None, max_content_length)
    body.append(b" " * (max_content_length + 1))
    with pytest.raises(RequestEntityTooLarge):
        await body
