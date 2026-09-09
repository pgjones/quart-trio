from __future__ import annotations

from asyncio import QueueEmpty, QueueShutDown
from os import PathLike
from typing import Generic, TypeVar

import trio
from quart.datastructures import FileStorage
from trio import open_file, Path, wrap_file

T = TypeVar("T")


class TrioQueue(Generic[T]):
    """Queue operations used by Quart's body and websocket buffers."""

    def __init__(self) -> None:
        self._send, self._receive = trio.open_memory_channel[T](float("inf"))

    async def put(self, value: T) -> None:
        try:
            await self._send.send(value)
        except trio.ClosedResourceError:
            raise QueueShutDown from None

    def put_nowait(self, value: T) -> None:
        try:
            self._send.send_nowait(value)
        except trio.ClosedResourceError:
            raise QueueShutDown from None

    async def get(self) -> T:
        try:
            return await self._receive.receive()
        except trio.EndOfChannel:
            raise QueueShutDown from None

    def get_nowait(self) -> T:
        try:
            return self._receive.receive_nowait()
        except trio.WouldBlock:
            raise QueueEmpty from None
        except trio.EndOfChannel:
            raise QueueShutDown from None

    def empty(self) -> bool:
        return self._receive.statistics().current_buffer_used == 0

    def shutdown(self) -> None:
        self._send.close()


class TrioFileStorage(FileStorage):
    async def save(self, destination: PathLike, buffer_size: int = 16384) -> None:  # type: ignore
        wrapped_stream = wrap_file(self.stream)
        async with await open_file(destination, "wb") as file_:
            data = await wrapped_stream.read(buffer_size)
            while data != b"":
                await file_.write(data)
                data = await wrapped_stream.read(buffer_size)

    async def load(self, source: PathLike, buffer_size: int = 16384) -> None:
        path = Path(source)
        self.filename = path.name
        wrapped_stream = wrap_file(self.stream)
        async with await open_file(path, "rb") as file_:
            data = await file_.read(buffer_size)
            while data != b"":
                await wrapped_stream.write(data)
                data = await file_.read(buffer_size)
