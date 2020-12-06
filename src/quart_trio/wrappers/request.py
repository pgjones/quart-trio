from typing import AnyStr, Optional

import trio
from quart.exceptions import RequestEntityTooLarge, RequestTimeout
from quart.wrappers.request import Body, Request


class EventWrapper:
    def __init__(self) -> None:
        self._event = trio.Event()

    def clear(self) -> None:
        self._event = trio.Event()

    async def wait(self) -> None:
        await self._event.wait()

    def set(self) -> None:
        self._event.set()


class TrioBody(Body):
    def __init__(
        self, expected_content_length: Optional[int], max_content_length: Optional[int]
    ) -> None:
        self._data = bytearray()
        self._complete = EventWrapper()  # type: ignore
        self._has_data = EventWrapper()  # type: ignore
        self._max_content_length = max_content_length
        # Exceptions must be raised within application (not ASGI)
        # calls, this is achieved by having the ASGI methods set this
        # to an exception on error.
        self._must_raise: Optional[Exception] = None
        if (
            expected_content_length is not None
            and max_content_length is not None
            and expected_content_length > max_content_length
        ):
            self._must_raise = RequestEntityTooLarge()


class TrioRequest(Request):
    body_class = TrioBody

    async def get_data(self, raw: bool = True) -> AnyStr:
        if self.body_timeout is not None:
            with trio.move_on_after(self.body_timeout) as cancel_scope:
                return await self.body
        else:
            return await self.body
        if cancel_scope.cancelled_caught:
            raise RequestTimeout()
