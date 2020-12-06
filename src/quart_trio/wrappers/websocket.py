from typing import AnyStr

from quart.wrappers.websocket import Websocket


class TrioWebsocket(Websocket):
    async def send(self, data: AnyStr) -> None:
        await self.accept()
        await self._send(data)
