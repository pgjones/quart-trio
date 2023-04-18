from __future__ import annotations

from os import PathLike

from quart.datastructures import FileStorage
from trio import open_file, Path, wrap_file


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
