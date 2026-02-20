"""Telemetry and observability helpers for semantic search."""

from .instrumentation import instrument_stage, timed_stage
from .trace import (
    SearchTrace,
    get_current_trace,
    reset_current_trace,
    set_current_trace,
)

__all__ = [
    "SearchTrace",
    "get_current_trace",
    "instrument_stage",
    "reset_current_trace",
    "set_current_trace",
    "timed_stage",
]
