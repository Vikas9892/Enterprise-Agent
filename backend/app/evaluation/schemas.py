"""Data schemas and evaluation metrics for agent benchmarking suites."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvalMetricName(str, Enum):
    """Evaluation metric dimensions."""

    ACCURACY = "accuracy"
    TOOL_SELECTION = "tool_selection"
    SAFETY = "safety"
    POLICY_COMPLIANCE = "policy_compliance"
    LATENCY_BUDGET = "latency_budget"


class EvalTestCase(BaseModel):
    """An individual standardized evaluation scenario."""

    id: str
    name: str
    query: str
    persona: str = "coordinator"
    expected_tools: List[str] = Field(default_factory=list)
    forbidden_tools: List[str] = Field(default_factory=list)
    expected_keywords: List[str] = Field(default_factory=list)
    forbidden_keywords: List[str] = Field(default_factory=list)
    requires_human_approval: Optional[bool] = None
    max_latency_seconds: float = 20.0


class EvalDataset(BaseModel):
    """A collection of test cases grouped into an evaluation benchmark dataset."""

    id: str
    name: str
    description: str
    category: str
    test_cases: List[EvalTestCase] = Field(default_factory=list)


class EvalMetricScore(BaseModel):
    """Result of evaluating a single metric dimension on a test case."""

    metric_name: EvalMetricName
    score: float = Field(..., ge=0.0, le=1.0)
    passed: bool
    details: str = ""


class EvalTestCaseResult(BaseModel):
    """Aggregated evaluation outcome for a single test case."""

    test_id: str
    passed: bool
    score: float
    metric_scores: List[EvalMetricScore] = Field(default_factory=list)
    actual_tools_called: List[str] = Field(default_factory=list)
    actual_status: str
    actual_final_answer: Optional[str] = None
    latency_seconds: float = 0.0
    requires_human_approval: bool = False
    error: Optional[str] = None


class BenchmarkReport(BaseModel):
    """Complete summary report of an evaluation benchmark execution."""

    benchmark_id: str
    dataset_id: str
    dataset_name: str
    total_cases: int
    passed_cases: int
    pass_rate: float
    mean_score: float
    mean_latency_seconds: float
    created_at: str
    results: List[EvalTestCaseResult] = Field(default_factory=list)


class RunBenchmarkRequest(BaseModel):
    """API payload to initiate an evaluation benchmark."""

    dataset_id: str = Field(..., description="ID of the benchmark dataset to execute")
