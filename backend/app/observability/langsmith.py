"""LangSmith and OpenLLMetry-compatible trace run exporter and tracking logger."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class LangSmithRun:
    """Represents an observable unit of execution (LLM call, agent chain, or tool)."""

    def __init__(
        self,
        name: str,
        run_type: str,
        inputs: Dict[str, Any],
        run_id: Optional[str] = None,
        parent_run_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        project_name: Optional[str] = None,
    ) -> None:
        self.id = run_id or str(uuid.uuid4())
        self.name = name
        self.run_type = run_type
        self.inputs = inputs
        self.outputs: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.parent_run_id = parent_run_id
        self.start_time = datetime.now(timezone.utc).isoformat()
        self.end_time: Optional[str] = None
        self.tags = tags or []
        self.metadata = metadata or {}
        self.project_name = project_name or get_settings().langsmith_project

    def finish(self, outputs: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
        """Mark run as ended with outputs or exception message."""
        self.end_time = datetime.now(timezone.utc).isoformat()
        self.outputs = outputs
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert run to LangSmith API-compatible dictionary payload."""
        return {
            "id": self.id,
            "name": self.name,
            "run_type": self.run_type,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "error": self.error,
            "parent_run_id": self.parent_run_id,
            "tags": self.tags,
            "extra": {
                "metadata": self.metadata,
                "project_name": self.project_name,
            },
        }


class LangSmithTracer:
    """Client for logging LLM and agent runs to LangSmith or in-memory audit store."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._runs: List[LangSmithRun] = []
        self._runs_by_id: Dict[str, LangSmithRun] = {}
        self._max_runs = 1000

    @property
    def is_enabled(self) -> bool:
        """Check if LangSmith remote tracing is activated."""
        return bool(self.settings.langsmith_tracing and self.settings.langsmith_api_key)

    def start_run(
        self,
        name: str,
        run_type: str,
        inputs: Dict[str, Any],
        run_id: Optional[str] = None,
        parent_run_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LangSmithRun:
        """Create and begin tracking a new run."""
        run = LangSmithRun(
            name=name,
            run_type=run_type,
            inputs=inputs,
            run_id=run_id,
            parent_run_id=parent_run_id,
            tags=tags,
            metadata=metadata,
            project_name=self.settings.langsmith_project,
        )
        self._runs.append(run)
        self._runs_by_id[run.id] = run
        if len(self._runs) > self._max_runs:
            evicted = self._runs.pop(0)
            self._runs_by_id.pop(evicted.id, None)

        logger.debug("Started LangSmith run: %s (%s)", run.name, run.run_type)
        return run

    def end_run(
        self,
        run_id: str,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[LangSmithRun]:
        """Finish an active run and log results."""
        run = self._runs_by_id.get(run_id)
        if run:
            run.finish(outputs=outputs, error=error)
            logger.debug("Ended LangSmith run: %s (error=%s)", run.name, bool(error))
        return run

    def get_runs(self, limit: int = 100) -> List[LangSmithRun]:
        """Fetch recently recorded runs."""
        return self._runs[-limit:]

    def clear(self) -> None:
        """Clear the in-memory run buffer."""
        self._runs.clear()
        self._runs_by_id.clear()


# Global singleton instance
langsmith_tracer = LangSmithTracer()


def get_langsmith_tracer() -> LangSmithTracer:
    """Return the global LangSmith tracer instance."""
    return langsmith_tracer
