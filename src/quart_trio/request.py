from typing import AnyStr, Optional

import trio
from quart.exceptions import RequestTimeout
from quart.wrappers.request import Body, Request, Websocket


class TrioBody(Body):
    def __init__(
        self, expected_content_length: Optional[int], max_content_length: Optional[int]
    ) -> None:
        super().__init__(expected_content_length, max_content_length)
        self._complete = trio.Event()
        self._has_data = trio.Event()


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


class TrioWebsocket(Websocket):
    async def send(self, data: AnyStr) -> None:
        # Must allow for the event loop to act if the user has say
        # setup a tight loop sending data over a websocket (as in the
        # example). So yield via the sleep.
        await trio.sleep(0)
        await self.accept()
        await self._send(data)
