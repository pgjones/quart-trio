from typing import AnyStr, Optional

import trio
from quart.wrappers.request import Body, Request
from werkzeug.exceptions import RequestEntityTooLarge, RequestTimeout

from ..formparser import TrioFormDataParser


class EventWrapper:
    def __init__(self) -> None:
        self._event = trio.Event()

    def clear(self) -> None:
        self._event = trio.Event()

    async def wait(self) -> None:
        await self._event.wait()

    def is_set(self) -> bool:
        return self._event.is_set()

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
    form_data_parser_class = TrioFormDataParser
    lock_class = trio.Lock  # type: ignore

    async def get_data(
        self, cache: bool = True, as_text: bool = False, parse_form_data: bool = False
    ) -> AnyStr:
        if parse_form_data:
            await self._load_form_data()

        timeout = float("inf") if self.body_timeout is None else self.body_timeout
        with trio.move_on_after(timeout) as cancel_scope:
            raw_data = await self.body
        if cancel_scope.cancelled_caught:
            raise RequestTimeout()

        if not cache:
            self.body.clear()

        if as_text:
            return raw_data.decode()
        else:
            return raw_data

    async def _load_form_data(self) -> None:
        async with self._parsing_lock:
            if self._form is None:
                parser = self.make_form_data_parser()

                timeout = float("inf") if self.body_timeout is None else self.body_timeout
                with trio.move_on_after(timeout) as cancel_scope:
                    self._form, self._files = await parser.parse(
                        self.body,
                        self.mimetype,
                        self.content_length,
                        self.mimetype_params,
                    )
                if cancel_scope.cancelled_caught:
                    raise RequestTimeout()
