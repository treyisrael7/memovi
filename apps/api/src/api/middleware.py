"""HTTP middleware for request context, access logs, and root spans."""

from __future__ import annotations

import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from memovi_observability import (
    RequestContext,
    bind_request_context,
    clear_request_context,
    get_logger,
    get_metrics_recorder,
    start_span,
)
from memovi_observability.logging.structured import log_operation

REQUEST_ID_HEADER = "X-Request-Id"
CORRELATION_ID_HEADER = "X-Correlation-Id"
LOGGER = get_logger("memovi.api.access")

# Local presentation clients (Tauri desktop shell + optional Next.js web).
LOCAL_CLIENT_ORIGINS = (
    "http://localhost:1420",
    "http://127.0.0.1:1420",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "tauri://localhost",
    "https://tauri.localhost",
    "http://tauri.localhost",
)


class RequestContextMiddleware:
    """Pure ASGI middleware to avoid BaseHTTPMiddleware request.state isolation."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        request_id = headers.get(REQUEST_ID_HEADER.lower()) or str(uuid.uuid4())
        correlation_id = headers.get(CORRELATION_ID_HEADER.lower())
        context = RequestContext.create(
            request_id=request_id,
            correlation_id=correlation_id,
        )
        state = scope.setdefault("state", {})
        state["request_context"] = context
        state["request_id"] = request_id
        state["correlation_id"] = correlation_id

        token = bind_request_context(context)
        started = time.perf_counter()
        status_code = 500
        path = scope.get("path", "")
        method = scope.get("method", "GET")

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                raw_headers = list(message.get("headers", []))
                raw_headers.append((REQUEST_ID_HEADER.lower().encode(), request_id.encode()))
                if correlation_id:
                    raw_headers.append(
                        (CORRELATION_ID_HEADER.lower().encode(), correlation_id.encode())
                    )
                message = {**message, "headers": raw_headers}
            await send(message)

        try:
            with start_span(
                f"HTTP {method} {path}",
                attributes={
                    "http.method": method,
                    "http.route": path,
                    "operation": "http.request",
                },
            ):
                await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = (time.perf_counter() - started) * 1000.0
            status = "success" if status_code < 400 else "error"
            get_metrics_recorder().timing(
                "memovi.http.request",
                duration_ms,
                tags={
                    "method": method,
                    "status_code": str(status_code),
                },
            )
            # Prefer the latest request.state context (includes workspace binding).
            state = scope.get("state", {})
            latest = (
                state.get("request_context")
                if isinstance(state, dict)
                else getattr(state, "request_context", None)
            )
            if latest is not None:
                bind_request_context(latest)
            log_operation(
                LOGGER,
                operation="http.request",
                status=status,
                duration_ms=duration_ms,
                http_method=method,
                http_path=path,
                http_status=status_code,
            )
            clear_request_context(token)


def register_middleware(app: FastAPI) -> None:
    app.add_middleware(RequestContextMiddleware)
    # Added last so CORS is the outermost layer and can answer preflight.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(LOCAL_CLIENT_ORIGINS),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
