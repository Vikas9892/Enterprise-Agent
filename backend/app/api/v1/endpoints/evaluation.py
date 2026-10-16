"""API endpoints for agent evaluation datasets, running benchmarks, and viewing reports."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.database.models.user import User
from app.evaluation.datasets import get_dataset, list_datasets
from app.evaluation.runner import EvaluationRunner, get_evaluation_runner
from app.evaluation.schemas import BenchmarkReport, EvalDataset, RunBenchmarkRequest

router = APIRouter()


@router.get(
    "/datasets",
    response_model=List[EvalDataset],
    summary="List Evaluation Datasets",
    description="Retrieve available evaluation benchmark datasets and scenarios.",
)
async def get_datasets() -> List[EvalDataset]:
    """List available benchmark datasets."""
    return list_datasets()


@router.get(
    "/datasets/{dataset_id}",
    response_model=EvalDataset,
    summary="Get Evaluation Dataset Details",
    description="Retrieve details and test cases for a specific evaluation dataset.",
)
async def get_dataset_detail(dataset_id: str) -> EvalDataset:
    """Fetch benchmark dataset by ID."""
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation dataset '{dataset_id}' not found.",
        )
    return dataset


@router.post(
    "/run",
    response_model=BenchmarkReport,
    summary="Run Evaluation Benchmark",
    description="Execute an evaluation benchmark against the agent orchestrator and return scores.",
)
async def run_benchmark(
    request: RunBenchmarkRequest,
    runner: EvaluationRunner = Depends(get_evaluation_runner),
    current_user: User = Depends(get_current_user),
) -> BenchmarkReport:
    """Execute a benchmark dataset and compile scoring report."""
    dataset = get_dataset(request.dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation dataset '{request.dataset_id}' not found.",
        )

    report = await runner.run_benchmark(dataset)
    return report


@router.get(
    "/benchmarks",
    response_model=List[BenchmarkReport],
    summary="List Benchmark Reports",
    description="List all historical evaluation benchmark reports.",
)
async def list_benchmark_reports(
    runner: EvaluationRunner = Depends(get_evaluation_runner),
) -> List[BenchmarkReport]:
    """Retrieve historical benchmark reports."""
    return runner.list_reports()


@router.get(
    "/benchmarks/{benchmark_id}",
    response_model=BenchmarkReport,
    summary="Get Benchmark Report",
    description="Retrieve detailed results for a specific benchmark run.",
)
async def get_benchmark_report(
    benchmark_id: str,
    runner: EvaluationRunner = Depends(get_evaluation_runner),
) -> BenchmarkReport:
    """Fetch report by benchmark ID."""
    report = runner.get_report(benchmark_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark report '{benchmark_id}' not found.",
        )
    return report
