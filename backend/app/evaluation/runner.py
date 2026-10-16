"""Benchmarking test runner executing evaluation datasets against AgentOrchestrator."""

import datetime
import logging
import time
from typing import Dict, List, Optional
import uuid

from app.agent.dependencies import get_agent_orchestrator
from app.agent.orchestrator import AgentOrchestrator
from app.evaluation.datasets import get_dataset
from app.evaluation.evaluators import CompositeEvaluator
from app.evaluation.schemas import (
    BenchmarkReport,
    EvalDataset,
    EvalTestCaseResult,
)
from app.observability.langsmith import get_langsmith_tracer
from app.observability.metrics import get_metrics

logger = logging.getLogger(__name__)


class EvaluationRunner:
    """Orchestrates test executions and evaluates agent responses across multiple benchmarks."""

    def __init__(self, orchestrator: Optional[AgentOrchestrator] = None) -> None:
        self.orchestrator = orchestrator
        self.evaluator = CompositeEvaluator()
        self._reports: Dict[str, BenchmarkReport] = {}

    def _get_orchestrator(self) -> AgentOrchestrator:
        if self.orchestrator is None:
            self.orchestrator = get_agent_orchestrator()
        return self.orchestrator

    async def run_benchmark(
        self,
        dataset: EvalDataset,
        orchestrator: Optional[AgentOrchestrator] = None,
    ) -> BenchmarkReport:
        """Run all test cases in the dataset and compile aggregate report."""
        orch = orchestrator or self._get_orchestrator()
        results: List[EvalTestCaseResult] = []
        metrics_collector = get_metrics()
        langsmith = get_langsmith_tracer()

        benchmark_id = f"bench-{uuid.uuid4().hex[:10]}"
        logger.info("Starting benchmark %s for dataset '%s'", benchmark_id, dataset.name)

        total_latency = 0.0

        for tc in dataset.test_cases:
            start_time = time.perf_counter()
            langsmith_run = langsmith.start_run(
                name=f"Eval [{tc.id}]: {tc.name}",
                run_type="chain",
                inputs={"query": tc.query, "persona": tc.persona},
                tags=["eval", dataset.id, tc.persona],
            )

            try:
                state = await orch.run_workflow(
                    query=tc.query,
                    persona_id=tc.persona,
                )
                latency = time.perf_counter() - start_time
                total_latency += latency

                tc_result = self.evaluator.evaluate(tc, state, latency)
                results.append(tc_result)

                langsmith.end_run(
                    run_id=langsmith_run.id,
                    outputs={"final_answer": state.final_answer, "scratchpad": state.scratchpad},
                )
            except Exception as exc:
                latency = time.perf_counter() - start_time
                total_latency += latency
                logger.error("Error executing eval test case %s: %s", tc.id, exc)
                # Create failure fallback state
                from app.agent.state import AgentState, AgentStatus
                empty_state = AgentState(
                    session_id=f"err-{uuid.uuid4().hex[:8]}",
                    input_query=tc.query,
                    status=AgentStatus.FAILED,
                )
                tc_result = self.evaluator.evaluate(tc, empty_state, latency, error=exc)
                results.append(tc_result)
                langsmith.end_run(run_id=langsmith_run.id, error=str(exc))

        passed_cases = sum(1 for r in results if r.passed)
        total_cases = len(results)
        pass_rate = round((passed_cases / total_cases) * 100.0, 2) if total_cases > 0 else 0.0
        mean_score = round(sum(r.score for r in results) / total_cases, 3) if total_cases > 0 else 0.0
        mean_latency = round(total_latency / total_cases, 3) if total_cases > 0 else 0.0

        report = BenchmarkReport(
            benchmark_id=benchmark_id,
            dataset_id=dataset.id,
            dataset_name=dataset.name,
            total_cases=total_cases,
            passed_cases=passed_cases,
            pass_rate=pass_rate,
            mean_score=mean_score,
            mean_latency_seconds=mean_latency,
            created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            results=results,
        )

        self._reports[benchmark_id] = report
        return report

    def get_report(self, benchmark_id: str) -> Optional[BenchmarkReport]:
        """Fetch historical report by benchmark ID."""
        return self._reports.get(benchmark_id)

    def list_reports(self) -> List[BenchmarkReport]:
        """Return all historical benchmark reports."""
        return list(self._reports.values())


# Global singleton instance
evaluation_runner = EvaluationRunner()


def get_evaluation_runner() -> EvaluationRunner:
    """Return the global evaluation runner singleton."""
    return evaluation_runner
