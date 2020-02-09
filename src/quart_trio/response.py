import os
from inspect import isasyncgen, isgenerator
from types import TracebackType
from typing import AsyncGenerator, Iterable, Optional, Union

import trio
from quart.wrappers.response import _raise_if_invalid_range, IterableBody, Response, ResponseBody

from .utils import run_sync_iterable


class TrioFileBody(ResponseBody):
    """Provides an async file accessor with range setting.

    The :attr:`Response.response` attribute must be async-iterable and
    yield bytes, which this wrapper does for a file. In addition it
    allows a range to be set on the file, thereby supporting
    conditional requests.

    Attributes:
        buffer_size: Size in bytes to load per iteration.
    """

    buffer_size = 8192

    def __init__(
        self, file_path: Union[str, bytes, os.PathLike], *, buffer_size: Optional[int] = None
    ) -> None:
        self.file_path = file_path
        self.size = os.path.getsize(self.file_path)
        self.begin = 0
        self.end = self.size
        if buffer_size is not None:
            self.buffer_size = buffer_size
        self.file: Optional[trio._file_io.AsyncIOWrapper] = None

    async def __aenter__(self) -> "TrioFileBody":
        self.file = await trio.open_file(self.file_path, mode="rb")
        await self.file.__aenter__()
        await self.file.seek(self.begin)
        return self

    async def __aexit__(self, exc_type: type, exc_value: BaseException, tb: TracebackType) -> None:
        await self.file.__aexit__(exc_type, exc_value, tb)

    def __aiter__(self) -> "TrioFileBody":
        return self

    async def __anext__(self) -> bytes:
        current = await self.file.tell()
        if current >= self.end:
            raise StopAsyncIteration()
        read_size = min(self.buffer_size, self.end - current)
        chunk = await self.file.read(read_size)

        if chunk:
            return chunk
        else:
            raise StopAsyncIteration()

    async def convert_to_sequence(self) -> bytes:
        result = bytearray()
        async with self as response:
            async for data in response:
                result.extend(data)
        return bytes(result)

    async def make_conditional(
        self, begin: int, end: Optional[int], max_partial_size: Optional[int] = None
    ) -> int:
        self.begin = begin
        self.end = self.size if end is None else end
        if max_partial_size is not None:
            self.end = min(self.begin + max_partial_size, self.end)
        _raise_if_invalid_range(self.begin, self.end, self.size)
        return self.size


class TrioIterableBody(IterableBody):
    def __init__(self, iterable: Union[AsyncGenerator[bytes, None], Iterable]) -> None:
        self.iter: AsyncGenerator[bytes, None]
        if isasyncgen(iterable):
            self.iter = iterable  # type: ignore
        elif isgenerator(iterable):
            self.iter = run_sync_iterable(iterable)  # type: ignore
        else:

            async def _aiter() -> AsyncGenerator[bytes, None]:
                for data in iterable:  # type: ignore
                    yield data

            self.iter = _aiter()


class TrioResponse(Response):
    file_body_class = TrioFileBody  # type: ignore
    iterable_body_class = TrioIterableBody
