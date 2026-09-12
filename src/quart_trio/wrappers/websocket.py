from quart.wrappers.websocket import Buffer, Websocket

from ..datastructures import TrioQueue


class TrioBuffer(Buffer):
    def __init__(self) -> None:
        self._queue = TrioQueue[bytes | str]()  # type: ignore


class TrioWebsocket(Websocket):
    buffer_class = TrioBuffer

    async def send(self, data: str | bytes) -> None:
        await self.accept()
        await self._send(data)
