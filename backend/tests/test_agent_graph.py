"""Unit tests for the asynchronous StateGraph engine and execution runtime."""

import pytest
from app.agent.graph import END, StateGraph
from app.agent.state import AgentState, AgentStatus


@pytest.fixture
def base_state() -> AgentState:
    """Fixture providing clean initial state."""
    return AgentState(
        session_id="test-session-001",
        input_query="Test state transitions",
    )


@pytest.mark.asyncio
async def test_linear_graph_execution(base_state):
    """Verify linear node-to-node execution in StateGraph."""
    graph_builder = StateGraph()

    async def step_one(s: AgentState) -> AgentState:
        s.scratchpad["step_1"] = "done"
        return s

    async def step_two(s: AgentState) -> AgentState:
        s.scratchpad["step_2"] = "done"
        s.status = AgentStatus.COMPLETED
        return s

    graph_builder.add_node("first", step_one)
    graph_builder.add_node("second", step_two)
    graph_builder.set_entry_point("first")
    graph_builder.add_edge("first", "second")
    graph_builder.add_edge("second", END)

    compiled = graph_builder.compile()
    final_state = await compiled.run(base_state)

    assert final_state.scratchpad["step_1"] == "done"
    assert final_state.scratchpad["step_2"] == "done"
    assert len(final_state.trace) == 2
    assert final_state.trace[0].node_name == "first"
    assert final_state.trace[1].node_name == "second"


@pytest.mark.asyncio
async def test_conditional_edges_routing(base_state):
    """Verify dynamic routing based on state values."""
    graph_builder = StateGraph()

    async def evaluator(s: AgentState) -> AgentState:
        s.metadata["score"] = 85
        return s

    async def path_high(s: AgentState) -> AgentState:
        s.scratchpad["result"] = "high"
        return s

    async def path_low(s: AgentState) -> AgentState:
        s.scratchpad["result"] = "low"
        return s

    def router(s: AgentState) -> str:
        return "high_score" if s.metadata.get("score", 0) >= 50 else "low_score"

    graph_builder.add_node("eval", evaluator)
    graph_builder.add_node("high", path_high)
    graph_builder.add_node("low", path_low)
    graph_builder.set_entry_point("eval")

    graph_builder.add_conditional_edges(
        "eval",
        router,
        {"high_score": "high", "low_score": "low"},
    )
    graph_builder.add_edge("high", END)
    graph_builder.add_edge("low", END)

    compiled = graph_builder.compile()
    final_state = await compiled.run(base_state)

    assert final_state.scratchpad["result"] == "high"


@pytest.mark.asyncio
async def test_cyclical_reflection_loop_termination(base_state):
    """Verify that state graph can loop cyclically and terminate upon condition."""
    graph_builder = StateGraph()

    async def loop_node(s: AgentState) -> AgentState:
        count = s.scratchpad.get("count", 0) + 1
        s.scratchpad["count"] = count
        return s

    def loop_router(s: AgentState) -> str:
        if s.scratchpad.get("count", 0) < 3:
            return "continue_loop"
        return "done"

    graph_builder.add_node("counter", loop_node)
    graph_builder.set_entry_point("counter")
    graph_builder.add_conditional_edges(
        "counter",
        loop_router,
        {"continue_loop": "counter", "done": END},
    )

    compiled = graph_builder.compile()
    final_state = await compiled.run(base_state)

    assert final_state.scratchpad["count"] == 3
    assert len(final_state.trace) == 3


@pytest.mark.asyncio
async def test_max_iterations_guardrail(base_state):
    """Verify safety guardrail prevents infinite loops."""
    base_state.max_iterations = 4
    graph_builder = StateGraph()

    async def infinite_loop(s: AgentState) -> AgentState:
        return s

    graph_builder.add_node("loop", infinite_loop)
    graph_builder.set_entry_point("loop")
    graph_builder.add_edge("loop", "loop")

    compiled = graph_builder.compile()
    final_state = await compiled.run(base_state)

    assert final_state.iterations > 4
    assert final_state.status == AgentStatus.COMPLETED


@pytest.mark.asyncio
async def test_streaming_graph_transitions(base_state):
    """Verify streaming yields step transitions sequentially."""
    graph_builder = StateGraph()

    async def step_a(s: AgentState) -> AgentState:
        return s

    async def step_b(s: AgentState) -> AgentState:
        return s

    graph_builder.add_node("A", step_a)
    graph_builder.add_node("B", step_b)
    graph_builder.set_entry_point("A")
    graph_builder.add_edge("A", "B")
    graph_builder.add_edge("B", END)

    compiled = graph_builder.compile()
    nodes_visited = []

    async for node_name, state in compiled.stream(base_state):
        nodes_visited.append(node_name)

    assert nodes_visited == ["A", "B"]
