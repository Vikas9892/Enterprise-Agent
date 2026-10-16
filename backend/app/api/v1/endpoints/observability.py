"""API endpoints for observability metrics, distributed traces, and audit logs."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.models.user import User
from app.database.repositories.audit_log import AuditLogRepository
from app.database.session import get_db
from app.observability.langsmith import get_langsmith_tracer
from app.observability.metrics import get_metrics
from app.observability.tracer import get_tracer

router = APIRouter()


class AuditLogEntryResponse(BaseModel):
    """Schema representing an immutable compliance audit trail entry."""

    id: int
    actor_id: Optional[int] = None
    action: str
    entity_type: str
    entity_id: str
    old_values: Optional[str] = None
    new_values: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: str


class TraceSpanResponse(BaseModel):
    """Schema representing a distributed trace span."""

    name: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    start_time: str
    end_time: Optional[str] = None
    duration_ms: float
    status: str
    error_message: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    events: List[Dict[str, Any]] = Field(default_factory=list)


@router.get(
    "/metrics",
    summary="Scrape Prometheus Telemetry Metrics",
    description="Returns plain text OpenMetrics / Prometheus metrics for platform monitoring.",
)
async def get_prometheus_metrics() -> Response:
    """Return metrics formatted for Prometheus scraping."""
    text_metrics = get_metrics().to_prometheus_format()
    return PlainTextResponse(
        content=text_metrics,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get(
    "/stats",
    summary="Platform Performance & Latency Stats",
    description="Returns aggregated JSON telemetry including uptime, request counts, and latency percentiles.",
)
async def get_platform_stats() -> Dict[str, Any]:
    """Return summary statistics of platform telemetry."""
    return get_metrics().get_summary()


@router.get(
    "/traces",
    response_model=List[TraceSpanResponse],
    summary="List Distributed Trace Spans",
    description="Query in-memory OpenTelemetry-compatible spans, optionally filtered by trace ID.",
)
async def get_traces(
    trace_id: Optional[str] = Query(default=None, description="Filter spans for a specific trace ID"),
    limit: int = Query(default=100, ge=1, le=500, description="Max spans to return"),
) -> List[TraceSpanResponse]:
    """Retrieve captured distributed trace spans."""
    spans = get_tracer().get_spans(trace_id=trace_id, limit=limit)
    return [TraceSpanResponse(**s.to_dict()) for s in spans]


@router.get(
    "/runs",
    summary="List LangSmith LLM / Agent Runs",
    description="Inspect recent LLM calls and agent workflow runs formatted for LangSmith tracing.",
)
async def get_langsmith_runs(
    limit: int = Query(default=50, ge=1, le=200, description="Max runs to return"),
) -> List[Dict[str, Any]]:
    """Return recently captured LangSmith runs."""
    runs = get_langsmith_tracer().get_runs(limit=limit)
    return [r.to_dict() for r in runs]


@router.get(
    "/audit",
    response_model=List[AuditLogEntryResponse],
    summary="Query Immutable Audit Trail",
    description="Query compliance and operational audit log entries filtered by entity or actor.",
)
async def get_audit_trail(
    entity_type: Optional[str] = Query(default=None, description="Domain entity type (e.g. 'order', 'agent')"),
    entity_id: Optional[str] = Query(default=None, description="Entity identifier"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[AuditLogEntryResponse]:
    """Query system and agent compliance audit logs."""
    repo = AuditLogRepository(db)
    if entity_type and entity_id:
        logs = repo.list_by_entity(entity_type=entity_type, entity_id=entity_id)
    else:
        logs = repo.list_by_actor(actor_id=current_user.id, limit=100)

    return [
        AuditLogEntryResponse(
            id=log.id,
            actor_id=log.actor_id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            old_values=log.old_values,
            new_values=log.new_values,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            created_at=log.created_at.isoformat(),
        )
        for log in logs
    ]
