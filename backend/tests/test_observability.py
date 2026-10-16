"""Unit and integration tests for distributed tracing, metrics, LangSmith exporter, and middleware."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, hash_password
from app.database.models import User
from app.database.repositories.audit_log import AuditLogRepository
from app.observability.langsmith import LangSmithTracer
from app.observability.metrics import MetricsCollector
from app.observability.tracer import Tracer


@pytest.fixture
def auth_headers(db_session: Session) -> dict:
    """Create test user and return Authorization headers."""
    email = "obs.tester@enterprise.ai"
    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            hashed_password=hash_password("ObsPassword123!"),
            full_name="Observability Tester",
            department="DevOps",
            is_active=True,
            is_superuser=False,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token(
        subject=str(user.id),
        extra_claims={"email": user.email, "roles": ["DevOps"], "permissions": []},
    )
    return {"Authorization": f"Bearer {token}"}


def test_tracer_span_creation_and_attributes():
    """Verify Span attribute, event, and duration calculation."""
    tracer = Tracer(service_name="test-service")
    span = tracer.start_span("test_operation", attributes={"env": "test"})
    assert span.name == "test_operation"
    assert span.attributes["env"] == "test"
    assert span.attributes["service.name"] == "test-service"
    assert span.trace_id is not None
    assert span.span_id is not None

    span.add_event("checkpoint_reached", {"step": 1})
    assert len(span.events) == 1

    span.finish(status="ok")
    assert span.end_time is not None
    assert span.duration_ms >= 0.0

    dumped = span.to_dict()
    assert dumped["name"] == "test_operation"
    assert dumped["status"] == "ok"
    assert "start_time" in dumped
    assert "events" in dumped


def test_tracer_nested_spans_and_context_propagation():
    """Verify child spans link to parent span ID via context."""
    tracer = Tracer()
    with tracer.span("parent_work") as parent:
        assert tracer.get_active_span() == parent
        with tracer.span("child_work") as child:
            assert child.parent_span_id == parent.span_id
            assert child.trace_id == parent.trace_id
            assert tracer.get_active_span() == child

        # After child exits, active span reverts to parent
        assert tracer.get_active_span() == parent

    # Verify spans were recorded in tracer buffer
    recorded = tracer.get_spans(trace_id=parent.trace_id)
    assert len(recorded) == 2
    span_names = [s.name for s in recorded]
    assert "child_work" in span_names
    assert "parent_work" in span_names


@pytest.mark.asyncio
async def test_tracer_async_context_manager_and_error_recording():
    """Verify async span handles exceptions and marks status=error."""
    tracer = Tracer()
    with pytest.raises(ValueError):
        async with tracer.async_span("failing_async_task") as span:
            span.set_attribute("task.id", 42)
            raise ValueError("Something went wrong")

    recorded = tracer.get_spans(trace_id=span.trace_id)
    assert len(recorded) >= 1
    failed_span = recorded[-1]
    assert failed_span.status == "error"
    assert "Something went wrong" in (failed_span.error_message or "")


def test_metrics_collector_operations():
    """Verify counter, gauge, and histogram aggregation in MetricsCollector."""
    mc = MetricsCollector()

    # Counter
    mc.increment_counter("test_counter", 5.0, {"label_a": "val1"})
    mc.increment_counter("test_counter", 3.0, {"label_a": "val1"})

    # Gauge
    mc.set_gauge("active_workers", 8.0, {"pool": "agent"})

    # Histogram
    mc.observe_histogram("task_latency", 0.150, {"tier": "gold"})
    mc.observe_histogram("task_latency", 0.350, {"tier": "gold"})

    # Domain helpers
    mc.record_http_request("GET", "/api/v1/orders", 200, 0.045)
    mc.record_llm_request("gpt-4o", "success", 0.85, prompt_tokens=100, completion_tokens=50)
    mc.record_agent_run("coordinator", "completed", 1.25)
    mc.record_agent_step("plan")
    mc.record_tool_execution("get_customer", "success")
    mc.record_hitl_decision("coordinator", "approved")

    summary = mc.get_summary()
    assert summary["http"]["total_requests"] >= 1
    assert summary["llm"]["total_calls"] >= 1
    assert summary["llm"]["total_tokens"] == 150
    assert summary["agent"]["total_runs"] >= 1


def test_metrics_collector_prometheus_export():
    """Verify prometheus text formatting output."""
    mc = MetricsCollector()
    mc.increment_counter("http_requests_total", 10.0, {"method": "GET", "status": "200"})
    mc.set_gauge("memory_usage_bytes", 1048576.0)

    text = mc.to_prometheus_format()
    assert "# HELP" in text
    assert 'http_requests_total{method="GET",status="200"} 10.0' in text
    assert "memory_usage_bytes 1048576.0" in text


def test_langsmith_tracer_run_lifecycle():
    """Verify creating, tagging, and finalizing LangSmith runs."""
    lst = LangSmithTracer()
    run = lst.start_run(
        name="test_chain",
        run_type="chain",
        inputs={"query": "Hello world"},
        tags=["unit_test", "v1"],
        metadata={"user": "developer"},
    )
    assert run.id is not None
    assert run.name == "test_chain"
    assert run.tags == ["unit_test", "v1"]

    lst.end_run(run.id, outputs={"result": "Processed"})
    assert run.end_time is not None
    assert run.outputs == {"result": "Processed"}

    payload = run.to_dict()
    assert payload["run_type"] == "chain"
    assert payload["inputs"] == {"query": "Hello world"}
    assert payload["extra"]["metadata"]["user"] == "developer"


def test_observability_middleware_response_headers(client: TestClient):
    """Verify middleware injects X-Trace-ID and latency into HTTP responses."""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    assert "x-trace-id" in response.headers
    assert "x-request-id" in response.headers
    assert "x-response-time-ms" in response.headers


def test_observability_endpoints(client: TestClient, auth_headers: dict, db_session: Session):
    """Verify /observability/metrics, /stats, /traces, /runs, and /audit endpoints."""
    # 1. Metrics endpoint (Prometheus format)
    metrics_resp = client.get("/api/v1/observability/metrics")
    assert metrics_resp.status_code == status.HTTP_200_OK
    assert "text/plain" in metrics_resp.headers["content-type"]
    assert "# HELP" in metrics_resp.text

    # 2. Stats endpoint (JSON summary)
    stats_resp = client.get("/api/v1/observability/stats")
    assert stats_resp.status_code == status.HTTP_200_OK
    stats_data = stats_resp.json()
    assert "uptime_seconds" in stats_data
    assert "http" in stats_data
    assert "llm" in stats_data

    # 3. Traces endpoint
    traces_resp = client.get("/api/v1/observability/traces")
    assert traces_resp.status_code == status.HTTP_200_OK
    assert isinstance(traces_resp.json(), list)

    # 4. Runs endpoint
    runs_resp = client.get("/api/v1/observability/runs")
    assert runs_resp.status_code == status.HTTP_200_OK
    assert isinstance(runs_resp.json(), list)

    # 5. Seed an audit log and query via audit endpoint
    audit_repo = AuditLogRepository(db_session)
    audit_repo.log_event(
        action="update_status",
        entity_type="order",
        entity_id="ORD-2026-9001",
        actor_id=None,
        new_values={"status": "shipped"},
    )
    db_session.commit()

    audit_resp = client.get(
        "/api/v1/observability/audit?entity_type=order&entity_id=ORD-2026-9001",
        headers=auth_headers,
    )
    assert audit_resp.status_code == status.HTTP_200_OK
    audit_data = audit_resp.json()
    assert isinstance(audit_data, list)
    assert len(audit_data) >= 1
    assert audit_data[0]["entity_id"] == "ORD-2026-9001"
