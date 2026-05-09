"""ASGI middleware for request IDs and request logging."""

from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
logger = logging.getLogger("app.request")


def get_request_id() -> str:
    return _request_id_ctx.get()


class _RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_ctx.get()  # type: ignore[attr-defined]
        return True


_filter = _RequestIDFilter()
logging.getLogger().addFilter(_filter)


class RequestIDMiddleware:
    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID") -> None:
        self.app = app
        self.header_name = header_name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = headers.get(self.header_name) or str(uuid.uuid4())
        token = _request_id_ctx.set(request_id)
        start_time = time.perf_counter()
        status_code = 500
        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code, response_started

            if message["type"] == "http.response.start":
                response_started = True
                status_code = int(message["status"])
                mutable_headers = MutableHeaders(raw=list(message.get("headers", [])))
                mutable_headers[self.header_name] = request_id
                message["headers"] = mutable_headers.raw
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception(
                "HTTP %s %s -> 500 in %.2fms endpoint=%s client=%s query=%s",
                scope.get("method", "-"),
                scope.get("path", "-"),
                duration_ms,
                _resolve_endpoint_name(scope),
                _resolve_client_host(scope, headers),
                scope.get("query_string", b"").decode("utf-8") or "-",
            )
            raise
        finally:
            if response_started:
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                log_level = logging.INFO
                if status_code >= 500:
                    log_level = logging.ERROR
                elif status_code >= 400:
                    log_level = logging.WARNING
                logger.log(
                    log_level,
                    "HTTP %s %s -> %s in %.2fms endpoint=%s client=%s query=%s",
                    scope.get("method", "-"),
                    scope.get("path", "-"),
                    status_code,
                    duration_ms,
                    _resolve_endpoint_name(scope),
                    _resolve_client_host(scope, headers),
                    scope.get("query_string", b"").decode("utf-8") or "-",
                )
            _request_id_ctx.reset(token)


def _resolve_endpoint_name(scope: Scope) -> str:
    endpoint = scope.get("endpoint")
    if endpoint is None:
        return "-"
    return getattr(endpoint, "__name__", str(endpoint))


def _resolve_client_host(scope: Scope, headers: Headers) -> str:
    forwarded_for = headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    client = scope.get("client")
    if client and client[0]:
        return str(client[0])
    return "-"
