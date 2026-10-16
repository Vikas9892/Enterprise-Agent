"""Unit and integration tests for agent evaluation metrics, datasets, runner, and API endpoints."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.agent.orchestrator import AgentOrchestrator
from app.agent.state import AgentState, AgentStatus
from app.auth.security import create_access_token, hash_password
from app.database.models import User
from app.evaluation.datasets import get_dataset, list_datasets
from app.evaluation.evaluators import (
    AccuracyEvaluator,
    LatencyBudgetEvaluator,
    PolicyComplianceEvaluator,
    SafetyEvaluator,
    ToolSelectionEvaluator,
)
from app.evaluation.runner import EvaluationRunner
from app.evaluation.schemas import EvalMetricName, EvalTestCase


@pytest.fixture
def auth_headers(db_session: Session) -> dict:
    """Create test user and return Authorization headers."""
    email = "eval.tester@enterprise.ai"
    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            hashed_password=hash_password("EvalPass123!"),
            full_name="Evaluation Tester",
            department="QA & Safety",
            is_active=True,
            is_superuser=False,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token(
        subject=str(user.id),
        extra_claims={"email": user.email, "roles": ["QA"], "permissions": []},
    )
    return {"Authorization": f"Bearer {token}"}


def test_accuracy_evaluator():
    """Verify AccuracyEvaluator computes keyword recall correctly."""
    evaluator = AccuracyEvaluator()
    tc = EvalTestCase(
        id="t-1",
        name="Accuracy Check",
        query="Check account status",
        expected_keywords=["Apex", "Gold", "Priority"],
    )

    state = AgentState(
        session_id="s-1",
        input_query="Check account status",
        final_answer="Account Apex is on Enterprise Gold tier with Priority support.",
    )
    score = evaluator.evaluate(tc, state)
    assert score.metric_name == EvalMetricName.ACCURACY
    assert score.passed is True
    assert score.score == 1.0


def test_tool_selection_evaluator():
    """Verify ToolSelectionEvaluator checks expected and forbidden tools."""
    evaluator = ToolSelectionEvaluator()
    tc = EvalTestCase(
        id="t-2",
        name="Tool Check",
        query="Order details",
        expected_tools=["get_order_details"],
        forbidden_tools=["delete_order"],
    )

    # Valid execution
    state_valid = AgentState(
        session_id="s-2",
        input_query="Order details",
        scratchpad={"get_order_details": {"status": "shipped"}},
    )
    score_valid = evaluator.evaluate(tc, state_valid)
    assert score_valid.passed is True
    assert score_valid.score == 1.0

    # Forbidden tool executed
    state_invalid = AgentState(
        session_id="s-3",
        input_query="Order details",
        scratchpad={"get_order_details": {}, "delete_order": {}},
    )
    score_invalid = evaluator.evaluate(tc, state_invalid)
    assert score_invalid.passed is False
    assert score_invalid.score == 0.0


def test_safety_evaluator():
    """Verify SafetyEvaluator flags prompt injection and forbidden phrases."""
    evaluator = SafetyEvaluator()
    tc = EvalTestCase(
        id="t-4",
        name="Safety Check",
        query="Test query",
        forbidden_keywords=["secret_token_123"],
    )

    # Clean state
    state_safe = AgentState(
        session_id="s-4",
        input_query="Test query",
        final_answer="All systems operational.",
    )
    assert evaluator.evaluate(tc, state_safe).passed is True

    # Leaked token
    state_unsafe = AgentState(
        session_id="s-5",
        input_query="Test query",
        final_answer="The token is secret_token_123.",
    )
    assert evaluator.evaluate(tc, state_unsafe).passed is False


def test_policy_compliance_evaluator():
    """Verify PolicyComplianceEvaluator asserts HITL requirement."""
    evaluator = PolicyComplianceEvaluator()
    tc = EvalTestCase(
        id="t-6",
        name="HITL Check",
        query="Refund 1500",
        requires_human_approval=True,
    )

    state_compliant = AgentState(
        session_id="s-6",
        input_query="Refund 1500",
        requires_human_approval=True,
    )
    assert evaluator.evaluate(tc, state_compliant).passed is True

    state_non_compliant = AgentState(
        session_id="s-7",
        input_query="Refund 1500",
        requires_human_approval=False,
    )
    assert evaluator.evaluate(tc, state_non_compliant).passed is False


def test_latency_budget_evaluator():
    """Verify LatencyBudgetEvaluator compares duration against ceiling."""
    evaluator = LatencyBudgetEvaluator()
    tc = EvalTestCase(id="t-8", name="Latency Check", query="ping", max_latency_seconds=5.0)

    assert evaluator.evaluate(tc, latency_seconds=2.1).passed is True
    assert evaluator.evaluate(tc, latency_seconds=7.5).passed is False


def test_evaluation_datasets_registry():
    """Verify standard benchmark datasets are loaded and queryable."""
    datasets = list_datasets()
    assert len(datasets) >= 3

    cs = get_dataset("customer_support_eval")
    assert cs is not None
    assert len(cs.test_cases) >= 2

    log = get_dataset("logistics_fulfillment_eval")
    assert log is not None

    gov = get_dataset("governance_hitl_eval")
    assert gov is not None


@pytest.mark.asyncio
async def test_evaluation_runner_execution():
    """Verify EvaluationRunner executes a benchmark dataset and aggregates results."""
    runner = EvaluationRunner()
    dataset = get_dataset("customer_support_eval")
    assert dataset is not None

    report = await runner.run_benchmark(dataset)
    assert report.benchmark_id.startswith("bench-")
    assert report.total_cases == len(dataset.test_cases)
    assert report.passed_cases >= 1
    assert report.pass_rate > 0.0
    assert report.mean_score > 0.0
    assert len(report.results) == len(dataset.test_cases)

    # Verify report is cached in runner
    cached = runner.get_report(report.benchmark_id)
    assert cached is not None
    assert cached.benchmark_id == report.benchmark_id


def test_evaluation_api_endpoints(client: TestClient, auth_headers: dict):
    """Verify /evaluation/datasets, /run, and /benchmarks REST endpoints."""
    # 1. List datasets
    list_resp = client.get("/api/v1/evaluation/datasets")
    assert list_resp.status_code == status.HTTP_200_OK
    datasets = list_resp.json()
    assert isinstance(datasets, list)
    assert len(datasets) >= 3

    # 2. Get specific dataset
    get_resp = client.get("/api/v1/evaluation/datasets/customer_support_eval")
    assert get_resp.status_code == status.HTTP_200_OK
    assert get_resp.json()["id"] == "customer_support_eval"

    # 3. Run benchmark unauthorized
    unauth_run = client.post("/api/v1/evaluation/run", json={"dataset_id": "customer_support_eval"})
    assert unauth_run.status_code == status.HTTP_401_UNAUTHORIZED

    # 4. Run benchmark authorized
    run_resp = client.post(
        "/api/v1/evaluation/run",
        json={"dataset_id": "customer_support_eval"},
        headers=auth_headers,
    )
    assert run_resp.status_code == status.HTTP_200_OK
    report_data = run_resp.json()
    assert "benchmark_id" in report_data
    assert report_data["total_cases"] >= 2
    assert report_data["pass_rate"] > 0.0
    bench_id = report_data["benchmark_id"]

    # 5. List benchmarks
    bench_list_resp = client.get("/api/v1/evaluation/benchmarks")
    assert bench_list_resp.status_code == status.HTTP_200_OK
    benchmarks = bench_list_resp.json()
    assert any(b["benchmark_id"] == bench_id for b in benchmarks)

    # 6. Get benchmark by ID
    single_bench_resp = client.get(f"/api/v1/evaluation/benchmarks/{bench_id}")
    assert single_bench_resp.status_code == status.HTTP_200_OK
    assert single_bench_resp.json()["benchmark_id"] == bench_id
