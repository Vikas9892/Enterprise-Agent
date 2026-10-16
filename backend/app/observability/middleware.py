"""FastAPI HTTP middleware for distributed trace propagation, metrics collection, and request logging."""

import time
from typing import Callable
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger
from app.observability.metrics import metrics
from app.observability.tracer import tracer

logger = get_logger("app.observability.middleware")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware extracting trace IDs, recording HTTP metrics, and injecting trace headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or generate trace identifier
        trace_id = (
            request.headers.get("X-Trace-ID")
            or request.headers.get("x-trace-id")
            or request.headers.get("traceparent")
            or uuid.uuid4().hex
        )
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]

        # Attach to request state for downstream handlers
        request.state.trace_id = trace_id
        request.state.request_id = request_id

        start_time = time.perf_counter()
        span = tracer.start_span(
            name=f"HTTP {request.method} {request.url.path}",
            trace_id=trace_id,
            attributes={
                "http.method": request.method,
                "http.url": str(request.url),
                "http.path": request.url.path,
                "http.client_ip": request.client.host if request.client else None,
                "http.user_agent": request.headers.get("user-agent"),
                "request_id": request_id,
            },
        )

        try:
            response = await call_next(request)
            duration_s = time.perf_counter() - start_time
            duration_ms = round(duration_s * 1000.0, 2)

            span.set_attribute("http.status_code", response.status_code)
            span.finish(status="ok" if response.status_code < 400 else "error")

            # Record Prometheus metrics
            metrics.record_http_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_seconds=duration_s,
            )

            # Inject trace propagation headers into outgoing response
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time-MS"] = str(duration_ms)

            return response

        except Exception as exc:
            duration_s = time.perf_counter() - start_time
            span.record_exception(exc)
            span.finish(status="error")

            metrics.record_http_request(
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_seconds=duration_s,
            )
            logger.error("Unhandled HTTP error in request: %s", exc, extra={"trace_id": trace_id, "path": request.url.path})
            raise
        finally:
            tracer.record_span(span)
