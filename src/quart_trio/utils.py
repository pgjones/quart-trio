from contextvars import copy_context
from functools import partial, wraps
from inspect import isgenerator
from typing import Any, AsyncGenerator, Callable, Coroutine, Generator

import trio


def run_sync(func: Callable[..., Any]) -> Callable[..., Coroutine[Any, None, None]]:
    """Ensure that the sync function is run without blocking.

    If the *func* is not a coroutine it will be wrapped such that it
    runs on a thread. This ensures that synchronous functions do not
    block the event loop.
    """

    @wraps(func)
    async def _wrapper(*args: Any, **kwargs: Any) -> Any:
        result = await trio.to_thread.run_sync(
            partial(copy_context().run, partial(func, *args, **kwargs))
        )
        if isgenerator(result):
            return run_sync_iterable(result)
        else:
            return result

    _wrapper._quart_async_wrapper = True  # type: ignore
    return _wrapper


def run_sync_iterable(iterable: Generator[Any, None, None]) -> AsyncGenerator[Any, None]:
    async def _gen_wrapper() -> AsyncGenerator[Any, None]:
        # Wrap the generator such that each iteration runs
        # in the executor. Then rationalise the raised
        # errors so that it ends.
        def _inner() -> Any:
            # https://bugs.python.org/issue26221
            # StopIteration errors are swallowed by the
            # run_in_exector method
            try:
                return next(iterable)
            except StopIteration:
                raise StopAsyncIteration()

        while True:
            try:
                yield await trio.to_thread.run_sync(partial(copy_context().run, _inner))
            except StopAsyncIteration:
                return

    return _gen_wrapper()
