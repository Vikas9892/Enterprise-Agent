"""Prometheus-compatible metrics collection and statistical aggregation."""

from collections import defaultdict
import threading
import time
from typing import Any, Dict, List, Optional, Tuple


class MetricsCollector:
    """Enterprise metrics aggregator tracking HTTP, LLM, Agent, and Tool telemetry."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Counters: (name, tuple_of_sorted_label_items) -> count
        self._counters: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], float] = defaultdict(float)
        # Gauges: (name, tuple_of_sorted_label_items) -> value
        self._gauges: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], float] = defaultdict(float)
        # Histograms: (name, tuple_of_sorted_label_items) -> list of observation floats
        self._histograms: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], List[float]] = defaultdict(list)
        self._start_time = time.time()

    def _labels_key(self, labels: Optional[Dict[str, str]]) -> Tuple[Tuple[str, str], ...]:
        if not labels:
            return ()
        return tuple(sorted((k, str(v)) for k, v in labels.items()))

    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a monotonic counter metric."""
        key = (name, self._labels_key(labels))
        with self._lock:
            self._counters[key] += value

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set current value of an instantaneous gauge metric."""
        key = (name, self._labels_key(labels))
        with self._lock:
            self._gauges[key] = value

    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record an observation in a distribution histogram."""
        key = (name, self._labels_key(labels))
        with self._lock:
            self._histograms[key].append(value)
            # Keep sample size manageable
            if len(self._histograms[key]) > 5000:
                self._histograms[key] = self._histograms[key][-5000:]

    # Domain helpers
    def record_http_request(self, method: str, path: str, status_code: int, duration_seconds: float) -> None:
        """Record HTTP transaction telemetry."""
        # Sanitize path to avoid unbounded cardinality
        clean_path = path.split("?")[0]
        status_family = f"{status_code // 100}xx"
        labels = {"method": method.upper(), "path": clean_path, "status": str(status_code), "family": status_family}
        self.increment_counter("http_requests_total", 1.0, labels)
        self.observe_histogram("http_request_duration_seconds", duration_seconds, {"method": method, "path": clean_path})

    def record_llm_request(
        self,
        model: str,
        status: str,
        latency_seconds: float,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> None:
        """Record multi-provider LLM gateway telemetry."""
        self.increment_counter("llm_requests_total", 1.0, {"model": model, "status": status})
        self.observe_histogram("llm_latency_seconds", latency_seconds, {"model": model})
        if prompt_tokens > 0:
            self.increment_counter("llm_tokens_total", float(prompt_tokens), {"model": model, "type": "prompt"})
        if completion_tokens > 0:
            self.increment_counter("llm_tokens_total", float(completion_tokens), {"model": model, "type": "completion"})
        if prompt_tokens + completion_tokens > 0:
            self.increment_counter("llm_tokens_total", float(prompt_tokens + completion_tokens), {"model": model, "type": "total"})

    def record_agent_run(self, persona: str, status: str, duration_seconds: Optional[float] = None) -> None:
        """Record state machine agent task execution."""
        self.increment_counter("agent_runs_total", 1.0, {"persona": persona, "status": status})
        if duration_seconds is not None:
            self.observe_histogram("agent_run_duration_seconds", duration_seconds, {"persona": persona})

    def record_agent_step(self, node: str) -> None:
        """Record execution of an individual state-graph node."""
        self.increment_counter("agent_steps_total", 1.0, {"node": node})

    def record_tool_execution(self, tool: str, status: str) -> None:
        """Record invocation of a local or MCP tool."""
        self.increment_counter("tool_executions_total", 1.0, {"tool": tool, "status": status})

    def record_hitl_decision(self, persona: str, decision: str) -> None:
        """Record Human-In-The-Loop approval or rejection decision."""
        self.increment_counter("hitl_decisions_total", 1.0, {"persona": persona, "decision": decision})

    def get_summary(self) -> Dict[str, Any]:
        """Return a structured summary of all system and operational metrics."""
        with self._lock:
            uptime = time.time() - self._start_time

            total_http = sum(v for (k, _), v in self._counters.items() if k == "http_requests_total")
            total_llm = sum(v for (k, _), v in self._counters.items() if k == "llm_requests_total")
            total_agent = sum(v for (k, _), v in self._counters.items() if k == "agent_runs_total")
            total_tokens = sum(
                v for (k, labels), v in self._counters.items() if k == "llm_tokens_total" and any(l[0] == "type" and l[1] == "total" for l in labels)
            )

            # Compute latency percentiles
            http_durations = [d for (k, _), vals in self._histograms.items() if k == "http_request_duration_seconds" for d in vals]
            llm_durations = [d for (k, _), vals in self._histograms.items() if k == "llm_latency_seconds" for d in vals]

            def _percentile(data: List[float], p: float) -> float:
                if not data:
                    return 0.0
                sorted_d = sorted(data)
                idx = int(len(sorted_d) * p)
                idx = min(idx, len(sorted_d) - 1)
                return round(sorted_d[idx], 4)

            return {
                "uptime_seconds": round(uptime, 2),
                "http": {
                    "total_requests": int(total_http),
                    "p50_duration_ms": round(_percentile(http_durations, 0.50) * 1000, 2),
                    "p95_duration_ms": round(_percentile(http_durations, 0.95) * 1000, 2),
                    "p99_duration_ms": round(_percentile(http_durations, 0.99) * 1000, 2),
                },
                "llm": {
                    "total_calls": int(total_llm),
                    "total_tokens": int(total_tokens),
                    "p50_latency_ms": round(_percentile(llm_durations, 0.50) * 1000, 2),
                    "p95_latency_ms": round(_percentile(llm_durations, 0.95) * 1000, 2),
                },
                "agent": {
                    "total_runs": int(total_agent),
                },
            }

    def to_prometheus_format(self) -> str:
        """Format metrics into Prometheus / OpenMetrics plain text representation."""
        lines: List[str] = ["# HELP enterprise_agent_metrics System metrics for Enterprise Agent Platform"]
        with self._lock:
            # Format counters
            for (name, label_pairs), val in sorted(self._counters.items()):
                if label_pairs:
                    labels_str = ",".join(f'{k}="{v}"' for k, v in label_pairs)
                    lines.append(f"{name}{{{labels_str}}} {val}")
                else:
                    lines.append(f"{name} {val}")

            # Format gauges
            for (name, label_pairs), val in sorted(self._gauges.items()):
                if label_pairs:
                    labels_str = ",".join(f'{k}="{v}"' for k, v in label_pairs)
                    lines.append(f"{name}{{{labels_str}}} {val}")
                else:
                    lines.append(f"{name} {val}")

            # Format histogram summaries (count, sum)
            for (name, label_pairs), vals in sorted(self._histograms.items()):
                if vals:
                    count = len(vals)
                    total_sum = sum(vals)
                    base_labels = dict(label_pairs)
                    labels_count = ",".join(f'{k}="{v}"' for k, v in sorted(base_labels.items()))
                    if labels_count:
                        lines.append(f"{name}_count{{{labels_count}}} {count}")
                        lines.append(f"{name}_sum{{{labels_count}}} {round(total_sum, 6)}")
                    else:
                        lines.append(f"{name}_count {count}")
                        lines.append(f"{name}_sum {round(total_sum, 6)}")

        lines.append("")
        return "\n".join(lines)

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._start_time = time.time()


# Global singleton metrics collector
metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    """Return the global metrics collector instance."""
    return metrics
