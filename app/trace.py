"""Trace IDs: created when a journey starts (an HTTP request) and carried into queued jobs."""

import contextvars
import uuid

trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")


def new_trace_id() -> str:
    return uuid.uuid4().hex
