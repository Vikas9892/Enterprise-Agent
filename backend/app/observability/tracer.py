"""Distributed tracing, OpenTelemetry-compatible spans, and context propagation."""

from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
import datetime
import time
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional
import uuid

_current_trace_id: ContextVar[Optional[str]] = ContextVar("current_trace_id", default=None)
_current_span: ContextVar[Optional["Span"]] = ContextVar("current_span", default=None)


class Span:
    """An individual span of work in a distributed trace."""

    def __init__(
        self,
        name: str,
        trace_id: str,
        span_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.name = name
        self.trace_id = trace_id
        self.span_id = span_id or uuid.uuid4().hex[:16]
        self.parent_span_id = parent_span_id
        self.attributes: Dict[str, Any] = attributes or {}
        self.start_time: float = time.time()
        self._start_perf: float = time.perf_counter()
        self.end_time: Optional[float] = None
        self.duration_ms: float = 0.0
        self.status: str = "ok"
        self.error_message: Optional[str] = None
        self.events: List[Dict[str, Any]] = []

    def set_attribute(self, key: str, value: Any) -> "Span":
        """Attach a metadata attribute to this span."""
        self.attributes[key] = value
        return self

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> "Span":
        """Record an annotated timestamped event within the span."""
        self.events.append(
            {
                "name": name,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "attributes": attributes or {},
            }
        )
        return self

    def record_exception(self, exception: Exception) -> "Span":
        """Mark span as failed and record exception details."""
        self.status = "error"
        self.error_message = str(exception)
        self.add_event("exception", {"exception.type": type(exception).__name__, "exception.message": str(exception)})
        return self

    def finish(self, status: Optional[str] = None, error: Optional[str] = None) -> None:
        """Mark span execution finished and compute latency."""
        self.end_time = time.time()
        self.duration_ms = round((time.perf_counter() - self._start_perf) * 1000.0, 3)
        if status:
            self.status = status
        if error:
            self.status = "error"
            self.error_message = error

    def to_dict(self) -> Dict[str, Any]:
        """Serialize span into an OpenTelemetry-compatible dictionary."""
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "start_time": datetime.datetime.fromtimestamp(self.start_time, tz=datetime.timezone.utc).isoformat(),
            "end_time": (
                datetime.datetime.fromtimestamp(self.end_time, tz=datetime.timezone.utc).isoformat()
                if self.end_time
                else None
            ),
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error_message": self.error_message,
            "attributes": self.attributes,
            "events": self.events,
        }


class Tracer:
    """Distributed tracer recording hierarchical spans with async context safety."""

    def __init__(self, service_name: str = "enterprise-agent") -> None:
        self.service_name = service_name
        self._spans: List[Span] = []
        self._max_stored_spans = 2000

    def get_active_trace_id(self) -> Optional[str]:
        """Return the current context trace ID if set."""
        return _current_trace_id.get()

    def get_active_span(self) -> Optional[Span]:
        """Return the current active span in the context."""
        return _current_span.get()

    def start_span(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Start a new span within the current or specified trace context."""
        active_trace = trace_id or _current_trace_id.get() or uuid.uuid4().hex
        parent_span = _current_span.get()
        effective_parent = parent_span_id or (parent_span.span_id if parent_span else None)

        span_attrs = {"service.name": self.service_name}
        if attributes:
            span_attrs.update(attributes)

        span = Span(
            name=name,
            trace_id=active_trace,
            parent_span_id=effective_parent,
            attributes=span_attrs,
        )
        return span

    def record_span(self, span: Span) -> None:
        """Record completed span into trace buffer."""
        self._spans.append(span)
        if len(self._spans) > self._max_stored_spans:
            self._spans = self._spans[-self._max_stored_spans :]

    @contextmanager
    def span(
        self,
        name: str,
        trace_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Generator[Span, None, None]:
        """Synchronous context manager for span tracing."""
        span = self.start_span(name=name, trace_id=trace_id, attributes=attributes)
        token_trace = _current_trace_id.set(span.trace_id)
        token_span = _current_span.set(span)
        try:
            yield span
            span.finish()
        except Exception as exc:
            span.record_exception(exc)
            span.finish()
            raise
        finally:
            self.record_span(span)
            _current_trace_id.reset(token_trace)
            _current_span.reset(token_span)

    @asynccontextmanager
    async def async_span(
        self,
        name: str,
        trace_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Span, None]:
        """Asynchronous context manager for span tracing."""
        span = self.start_span(name=name, trace_id=trace_id, attributes=attributes)
        token_trace = _current_trace_id.set(span.trace_id)
        token_span = _current_span.set(span)
        try:
            yield span
            span.finish()
        except Exception as exc:
            span.record_exception(exc)
            span.finish()
            raise
        finally:
            self.record_span(span)
            _current_trace_id.reset(token_trace)
            _current_span.reset(token_span)

    def get_spans(self, trace_id: Optional[str] = None, limit: int = 100) -> List[Span]:
        """Retrieve recent spans, optionally filtered by trace ID."""
        if trace_id:
            matched = [s for s in self._spans if s.trace_id == trace_id]
            return matched[-limit:]
        return self._spans[-limit:]

    def clear(self) -> None:
        """Clear recorded spans buffer."""
        self._spans.clear()


# Global singleton tracer
tracer = Tracer()


def get_tracer() -> Tracer:
    """Return the global tracer instance."""
    return tracer
