"""Cyclical reflection, self-evaluation, and human-in-the-loop decision logic."""

import logging
from typing import Any, Dict, List, Tuple
from app.agent.state import AgentState

logger = logging.getLogger(__name__)


def evaluate_state_and_reflect(
    state: AgentState,
    requires_approval_actions: List[str],
) -> Tuple[str, Dict[str, Any]]:
    """Evaluate current observations, detect errors or missing facts, and route next node.

    Returns:
        decision: One of 'continue_tools', 'wait_for_human', 'synthesize'
        reflection_data: Structured notes on the evaluation
    """
    last_results = state.last_tool_results

    # 1. Check if human-in-the-loop approval was triggered by tool results
    for res in last_results:
        tool_res = res.get("result", {})
        if isinstance(tool_res, dict) and tool_res.get("requires_human_approval"):
            logger.info("Human approval flagged by tool output: %s", tool_res)
            return "wait_for_human", {
                "decision": "wait_for_human",
                "reason": tool_res.get("reason", "Action requires human supervisory sign-off"),
                "action": {"tool": res.get("tool"), "details": tool_res},
            }

    # 2. Check if any pending tool call matches sensitive action keywords
    for tc in state.pending_tool_calls:
        tool_name = tc.get("name", "").lower()
        if any(action in tool_name for action in requires_approval_actions):
            return "wait_for_human", {
                "decision": "wait_for_human",
                "reason": f"Tool '{tool_name}' performs sensitive operations and requires approval.",
                "action": tc,
            }

    # 3. Check for tool execution errors
    has_errors = any(res.get("is_error") for res in last_results)
    if has_errors:
        logger.warning("Tool execution error detected in session %s", state.session_id)
        # Check if we still have remaining iterations to try alternative tools
        if state.iterations < state.max_iterations - 2:
            return "continue_tools", {
                "decision": "continue_tools",
                "reason": "Previous tool encountered an error; retrying or using fallback investigation.",
            }

    # 4. Check if we have more tools queued or planned
    if state.pending_tool_calls:
        return "continue_tools", {
            "decision": "continue_tools",
            "reason": f"{len(state.pending_tool_calls)} tool calls still queued in plan.",
        }

    # 5. Default: observations gathered, proceed to synthesis
    return "synthesize", {
        "decision": "synthesize",
        "reason": "Sufficient observations gathered to formulate complete response.",
    }
