from __future__ import annotations

from types import TracebackType

import trio
from quart.app import Quart
from quart.testing.app import DEFAULT_TIMEOUT, LifespanError
from quart.typing import TestClientProtocol


class TrioTestApp:
    def __init__(
        self,
        app: "Quart",
        startup_timeout: int = DEFAULT_TIMEOUT,
        shutdown_timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.app = app
        self.startup_timeout = startup_timeout
        self.shutdown_timeout = shutdown_timeout
        self._startup = trio.Event()
        self._shutdown = trio.Event()
        self._app_send_channel, self._app_receive_channel = trio.open_memory_channel[dict](10)
        self._nursery_manager: trio._core._run.NurseryManager  # type: ignore
        self._nursery: trio.Nursery

    def test_client(self) -> TestClientProtocol:
        return self.app.test_client()

    async def startup(self) -> None:
        scope = {"type": "lifespan", "asgi": {"spec_version": "2.0"}}
        self._nursery.start_soon(self.app, scope, self._asgi_receive, self._asgi_send)  # type: ignore # noqa: E501
        await self._app_send_channel.send({"type": "lifespan.startup"})
        with trio.fail_after(self.startup_timeout):
            await self._startup.wait()

    async def shutdown(self) -> None:
        await self._app_send_channel.send({"type": "lifespan.shutdown"})
        with trio.fail_after(self.shutdown_timeout):
            await self._shutdown.wait()

    async def __aenter__(self) -> "TrioTestApp":
        self._nursery_manager = trio.open_nursery()
        self._nursery = await self._nursery_manager.__aenter__()
        await self.startup()
        return self

    async def __aexit__(self, exc_type: type, exc_value: BaseException, tb: TracebackType) -> None:
        await self.shutdown()
        await self._nursery_manager.__aexit__(exc_type, exc_value, tb)

    async def _asgi_receive(self) -> dict:
        return await self._app_receive_channel.receive()

    async def _asgi_send(self, message: dict) -> None:
        if message["type"] == "lifespan.startup.complete":
            self._startup.set()
        elif message["type"] == "lifespan.shutdown.complete":
            self._shutdown.set()
        elif message["type"] == "lifespan.startup.failed":
            self._startup.set()
            raise LifespanError(f"Error during startup {message['message']}")
        elif message["type"] == "lifespan.shutdown.failed":
            self._shutdown.set()
            raise LifespanError(f"Error during shutdown {message['message']}")
