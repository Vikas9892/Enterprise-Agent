"""State machine graph engine with cyclical loops and conditional edges."""

import inspect
import logging
import time
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional, Tuple

from app.agent.state import AgentState, AgentStatus, AgentStepTrace

logger = logging.getLogger(__name__)

NodeCallable = Callable[[AgentState], Awaitable[AgentState]]
RouterCallable = Callable[[AgentState], str]

END = "__END__"


class StateGraph:
    """Asynchronous cyclical state graph compiler and runtime."""

    def __init__(self):
        self._nodes: Dict[str, NodeCallable] = {}
        self._edges: Dict[str, str] = {}
        self._conditional_edges: Dict[str, Tuple[RouterCallable, Dict[str, str]]] = {}
        self._entry_point: Optional[str] = None
        self._finish_points: set[str] = set()

    def add_node(self, name: str, func: NodeCallable) -> None:
        """Register a workflow execution node."""
        if name in self._nodes:
            raise ValueError(f"Node '{name}' already exists in graph.")
        self._nodes[name] = func

    def add_edge(self, from_node: str, to_node: str) -> None:
        """Register a deterministic directed edge between two nodes."""
        if from_node not in self._nodes:
            raise ValueError(f"Source node '{from_node}' does not exist.")
        self._edges[from_node] = to_node

    def add_conditional_edges(
        self,
        from_node: str,
        router: RouterCallable,
        path_map: Dict[str, str],
    ) -> None:
        """Register conditional branch routing based on agent state."""
        if from_node not in self._nodes:
            raise ValueError(f"Source node '{from_node}' does not exist.")
        self._conditional_edges[from_node] = (router, path_map)

    def set_entry_point(self, name: str) -> None:
        """Define initial node to execute."""
        if name not in self._nodes:
            raise ValueError(f"Entry node '{name}' is not registered.")
        self._entry_point = name

    def set_finish_point(self, name: str) -> None:
        """Designate node as terminal."""
        self._finish_points.add(name)

    def compile(self) -> "CompiledGraph":
        """Validate and compile graph into an executable state machine."""
        if not self._entry_point:
            raise ValueError("Graph entry point has not been set.")
        return CompiledGraph(
            nodes=self._nodes,
            edges=self._edges,
            conditional_edges=self._conditional_edges,
            entry_point=self._entry_point,
            finish_points=self._finish_points,
        )


class CompiledGraph:
    """Compiled state graph runtime executor."""

    def __init__(
        self,
        nodes: Dict[str, NodeCallable],
        edges: Dict[str, str],
        conditional_edges: Dict[str, Tuple[RouterCallable, Dict[str, str]]],
        entry_point: str,
        finish_points: set[str],
    ):
        self.nodes = nodes
        self.edges = edges
        self.conditional_edges = conditional_edges
        self.entry_point = entry_point
        self.finish_points = finish_points

    async def _execute_node(self, node_name: str, state: AgentState) -> Tuple[AgentState, float]:
        """Execute node function and measure elapsed latency."""
        start_time = time.perf_counter()
        func = self.nodes[node_name]

        if inspect.iscoroutinefunction(func):
            new_state = await func(state)
        else:
            new_state = func(state)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return new_state, elapsed_ms

    def _determine_next_node(self, current_node: str, state: AgentState) -> Optional[str]:
        """Resolve next node using conditional router or static edge."""
        if current_node in self.finish_points or current_node == END:
            return None

        # 1. Check conditional edges
        if current_node in self.conditional_edges:
            router, path_map = self.conditional_edges[current_node]
            decision = router(state)
            next_node = path_map.get(decision)
            if not next_node:
                raise ValueError(
                    f"Conditional router returned '{decision}' which is not in path_map for node '{current_node}'"
                )
            return None if next_node == END else next_node

        # 2. Check static edges
        if current_node in self.edges:
            next_node = self.edges[current_node]
            return None if next_node == END else next_node

        return None

    async def run(self, initial_state: AgentState) -> AgentState:
        """Execute state machine until completion, HITL pause, or iteration limit."""
        state = initial_state
        current_node: Optional[str] = self.entry_point

        while current_node is not None:
            # Iteration guardrail
            state.iterations += 1
            if state.iterations > state.max_iterations:
                logger.warning(
                    "Session %s reached max iterations (%d). Forcing completion.",
                    state.session_id,
                    state.max_iterations,
                )
                state.status = AgentStatus.COMPLETED
                if not state.final_answer:
                    state.final_answer = "Max reasoning iterations reached. Partial analysis gathered in scratchpad."
                break

            logger.info("Executing node '%s' for session %s", current_node, state.session_id)
            state, latency_ms = await self._execute_node(current_node, state)

            # Record step trace
            state.trace.append(
                AgentStepTrace(
                    step_number=len(state.trace) + 1,
                    node_name=current_node,
                    action=f"Executed {current_node}",
                    observation=str(state.last_tool_results) if state.last_tool_results else None,
                    reflection=f"Iteration {state.iterations}",
                    latency_ms=round(latency_ms, 2),
                    status=state.status,
                )
            )

            # If node paused execution for Human-In-The-Loop approval
            if state.status == AgentStatus.WAITING_FOR_HUMAN or state.requires_human_approval:
                logger.info(
                    "Session %s paused: Human approval required for pending action.",
                    state.session_id,
                )
                break

            # Resolve next node transition
            current_node = self._determine_next_node(current_node, state)

        return state

    async def stream(
        self, initial_state: AgentState
    ) -> AsyncIterator[Tuple[str, AgentState]]:
        """Yield (node_name, state) transitions asynchronously in real time."""
        state = initial_state
        current_node: Optional[str] = self.entry_point

        while current_node is not None:
            state.iterations += 1
            if state.iterations > state.max_iterations:
                state.status = AgentStatus.COMPLETED
                if not state.final_answer:
                    state.final_answer = "Max reasoning iterations reached."
                yield (current_node, state)
                break

            state, latency_ms = await self._execute_node(current_node, state)

            state.trace.append(
                AgentStepTrace(
                    step_number=len(state.trace) + 1,
                    node_name=current_node,
                    action=f"Executed {current_node}",
                    observation=str(state.last_tool_results) if state.last_tool_results else None,
                    latency_ms=round(latency_ms, 2),
                    status=state.status,
                )
            )

            yield (current_node, state)

            if state.status == AgentStatus.WAITING_FOR_HUMAN or state.requires_human_approval:
                break

            current_node = self._determine_next_node(current_node, state)
