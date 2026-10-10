"""API endpoints for discovering and executing enterprise MCP tools."""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.database.models.user import User
from app.mcp.client import MCPClient
from app.tools.registry import tool_registry

router = APIRouter()
mcp_client = MCPClient()


class ToolInvocationRequest(BaseModel):
    """Schema for invoking a registered enterprise tool."""

    name: str = Field(description="Name of the tool to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Input arguments for the tool")


class ToolInvocationResponse(BaseModel):
    """Schema representing tool execution result."""

    name: str
    result: Any
    status: str = "success"


@router.get(
    "/tools",
    summary="List enterprise tools",
    description="Discovers tools from the MCP server and returns the unified active tool catalog.",
)
async def list_enterprise_tools(
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Discover tools and return catalog."""
    try:
        # Discover remote MCP tools and register them
        discovered = await mcp_client.list_tools()
        if discovered:
            tool_registry.register_mcp_tools(discovered, mcp_client)
    except Exception:
        pass

    return tool_registry.list_tools()


@router.post(
    "/tools/call",
    response_model=ToolInvocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute enterprise tool",
    description="Dispatches a tool call dynamically via the ToolRegistry to the local handler or remote MCP server.",
)
async def execute_enterprise_tool(
    payload: ToolInvocationRequest,
    current_user: User = Depends(get_current_user),
) -> ToolInvocationResponse:
    """Execute a registered tool by name with arguments."""
    try:
        # If tool not found locally, try refreshing MCP catalog first
        if not tool_registry.get_tool(payload.name):
            discovered = await mcp_client.list_tools(force_refresh=True)
            tool_registry.register_mcp_tools(discovered, mcp_client)

        result = await tool_registry.execute(payload.name, payload.arguments)
        return ToolInvocationResponse(
            name=payload.name,
            result=result,
            status="success",
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{payload.name}' not found",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(exc)}",
        )
