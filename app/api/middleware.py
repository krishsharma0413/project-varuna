"""Trace middleware: every HTTP request starts a journey with a new trace ID."""

from __future__ import annotations

import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.log import log
from app.trace import new_trace_id, trace_id_var

QUIET_PATHS = {"/api/v1/health"}


class TraceMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        trace_id = new_trace_id()
        token = trace_id_var.set(trace_id)
        started = time.perf_counter()
        status = 500

        async def send_with_trace(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"] = [*message.get("headers", []), (b"x-trace-id", trace_id.encode())]
            await send(message)

        try:
            await self.app(scope, receive, send_with_trace)
        except Exception as exc:
            log.exception("unhandled error", exc, path=scope.get("path"))
            raise
        finally:
            path = scope.get("path", "")
            if path not in QUIET_PATHS:
                elapsed = round((time.perf_counter() - started) * 1000)
                line = f"{scope.get('method')} {path} {status} {elapsed}ms"
                if status >= 500:
                    log.error(line)
                elif scope.get("method") == "GET":
                    log.debug(line)
                else:
                    log.info(line)
            trace_id_var.reset(token)
