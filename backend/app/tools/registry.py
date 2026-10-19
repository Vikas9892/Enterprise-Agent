"""Enterprise tool registry for cataloging and executing local and MCP tools."""

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from app.core.logging import get_logger
from app.mcp.client import MCPClient
from app.mcp.schemas import MCPTool
from app.tools.builtin_tools import calculate, get_current_datetime, verify_policy_compliance
from app.tools.schemas import ToolMetadata

logger = get_logger("app.tools.registry")


@dataclass
class ToolDefinition:
    """Metadata describing a registered tool."""

    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Callable[..., Any]] = None
    source: str = "local"
    is_sensitive: bool = False
    requires_approval: bool = False


class ToolRegistry:
    """Central registry and dispatch engine for enterprise tools."""

    def __init__(self, register_defaults: bool = False) -> None:
        self._tools: Dict[str, ToolDefinition] = {}
        if register_defaults:
            self.register_builtin_tools()

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Optional[Callable[..., Any]] = None,
        source: str = "local",
        is_sensitive: bool = False,
        requires_approval: bool = False,
    ) -> None:
        """Register a new tool into the catalog."""
        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            source=source,
            is_sensitive=is_sensitive,
            requires_approval=requires_approval,
        )
        logger.debug(f"Registered tool '{name}' (source: {source})")

    def register_tool(
        self,
        name: str,
        func: Callable[..., Any],
        description: str,
        parameters: Dict[str, Any],
        is_sensitive: bool = False,
        requires_approval: bool = False,
    ) -> None:
        """Convenience method to register a local Python function tool."""
        self.register(
            name=name,
            description=description,
            parameters=parameters,
            handler=func,
            source="local",
            is_sensitive=is_sensitive,
            requires_approval=requires_approval,
        )

    def register_builtin_tools(self) -> None:
        """Register standard built-in local enterprise tools."""
        self.register_tool(
            name="get_current_datetime",
            func=get_current_datetime,
            description="Retrieve current enterprise server UTC timestamp and date.",
            parameters={"type": "object", "properties": {}},
        )
        self.register_tool(
            name="calculate",
            func=calculate,
            description="Safely evaluate mathematical expressions for financial/operational calculation.",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Mathematical formula to evaluate"}
                },
                "required": ["expression"],
            },
        )
        self.register_tool(
            name="verify_policy_compliance",
            func=verify_policy_compliance,
            description="Verify enterprise compliance rules and approval requirements for actions (refunds, cancellations).",
            parameters={
                "type": "object",
                "properties": {
                    "action_type": {"type": "string", "description": "Action being attempted, e.g. 'refund', 'cancel_order'"},
                    "amount": {"type": "number", "description": "Monetary value associated with the action"}
                },
                "required": ["action_type"],
            },
            is_sensitive=True,
        )
        from app.tools.builtin_tools import (
            check_inventory,
            get_customer,
            get_order_details,
            get_support_ticket,
            search_knowledge_base,
        )

        self.register_tool(
            name="get_customer",
            func=get_customer,
            description="Look up enterprise customer profile and account details.",
            parameters={
                "type": "object",
                "properties": {"customer_id": {"type": "string"}},
            },
        )
        self.register_tool(
            name="get_order_details",
            func=get_order_details,
            description="Look up enterprise order tracking and shipment line items.",
            parameters={
                "type": "object",
                "properties": {"order_number": {"type": "string"}},
            },
        )
        self.register_tool(
            name="check_inventory",
            func=check_inventory,
            description="Check inventory stock levels, warehouse, and availability.",
            parameters={
                "type": "object",
                "properties": {"sku": {"type": "string"}},
            },
        )
        self.register_tool(
            name="get_support_ticket",
            func=get_support_ticket,
            description="Look up enterprise customer support ticket history and SLA.",
            parameters={
                "type": "object",
                "properties": {"ticket_number": {"type": "string"}},
            },
        )
        self.register_tool(
            name="search_knowledge_base",
            func=search_knowledge_base,
            description="Search enterprise policies, manuals, SLA documentation, and standard operating procedures.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query or knowledge question"},
                    "category": {"type": "string", "description": "Optional category filter (finance, logistics, compliance)"},
                    "top_k": {"type": "integer", "description": "Number of reference passages to retrieve"},
                },
                "required": ["query"],
            },
        )

    def is_local_tool(self, name: str) -> bool:
        """Check if tool name belongs to local tools."""
        tool = self._tools.get(name)
        return bool(tool and tool.source == "local")

    def register_mcp_tools(
        self, tools: List[MCPTool], mcp_client: MCPClient
    ) -> None:
        """Register a list of remote tools discovered from an MCP server."""
        for tool in tools:
            # Create a closure binding the tool name and mcp_client
            async def handler_proxy(_name=tool.name, **kwargs):
                result = await mcp_client.call_tool(_name, kwargs)
                return result.content

            self.register(
                name=tool.name,
                description=tool.description,
                parameters=tool.input_schema,
                handler=handler_proxy,
                source="mcp",
            )

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Look up tool metadata by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return a serialized catalog of all available registered tools."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
                "source": t.source,
                "is_sensitive": t.is_sensitive,
                "requires_approval": t.requires_approval,
            }
            for t in self._tools.values()
        ]

    async def execute(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a registered tool by name with provided arguments."""
        tool = self.get_tool(name)
        if not tool:
            raise KeyError(f"Tool '{name}' not found in registry")
        if not tool.handler:
            raise ValueError(f"Tool '{name}' has no executable handler registered")

        logger.info(f"Executing tool '{name}'", extra={"tool": name, "arguments": arguments})

        if inspect.iscoroutinefunction(tool.handler):
            return await tool.handler(**arguments)
        else:
            return tool.handler(**arguments)

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool and return structured execution dictionary."""
        try:
            result = await self.execute(name, arguments)
            return {"tool": name, "result": result, "is_error": False}
        except Exception as exc:
            logger.error(f"Error executing tool '{name}': {exc}")
            return {"tool": name, "error": str(exc), "is_error": True}

    def to_openai_tools(self) -> List[Dict[str, Any]]:
        """Export tools formatted for OpenAI / LiteLLM function calling schemas."""
        schemas = []
        for tool in self._tools.values():
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
            )
        return schemas

    async def get_all_tool_definitions(self) -> List[Dict[str, Any]]:
        """Asynchronously return all tool definitions in OpenAI / LiteLLM format."""
        return self.to_openai_tools()


# Global singleton tool registry with built-in enterprise tools
tool_registry = ToolRegistry(register_defaults=True)


def get_tool_registry() -> ToolRegistry:
    """Return the global tool registry singleton instance."""
    return tool_registry
