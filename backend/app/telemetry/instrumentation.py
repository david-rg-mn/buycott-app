from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
from inspect import iscoroutinefunction
from time import perf_counter
from typing import Callable, ParamSpec, TypeVar

from .trace import get_current_trace

P = ParamSpec("P")
R = TypeVar("R")


@contextmanager
def timed_stage(stage: str):
    started = perf_counter()
    try:
        yield
    finally:
        trace = get_current_trace()
        if trace is None:
            return
        trace.record_stage_time(stage, (perf_counter() - started) * 1000.0)


def instrument_stage(stage: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        if iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs):  # type: ignore[misc]
                with timed_stage(stage):
                    return await func(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            with timed_stage(stage):
                return func(*args, **kwargs)

        return wrapper

    return decorator
