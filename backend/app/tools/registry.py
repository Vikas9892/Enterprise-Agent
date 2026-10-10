"""Enterprise tool registry for cataloging and executing local and MCP tools."""

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from app.core.logging import get_logger
from app.mcp.client import MCPClient
from app.mcp.schemas import MCPTool

logger = get_logger("app.tools.registry")


@dataclass
class ToolDefinition:
    """Metadata describing a registered tool."""

    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Callable[..., Any]] = None
    source: str = "local"


class ToolRegistry:
    """Central registry and dispatch engine for enterprise tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Optional[Callable[..., Any]] = None,
        source: str = "local",
    ) -> None:
        """Register a new tool into the catalog."""
        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            source=source,
        )
        logger.debug(f"Registered tool '{name}' (source: {source})")

    def register_mcp_tools(
        self, tools: List[MCPTool], mcp_client: MCPClient
    ) -> None:
        """Register a list of remote tools discovered from an MCP server."""
        for tool in tools:
            # Create a closure binding the tool name and mcp_client
            async def _create_mcp_handler(tool_name: str):
                async def _mcp_handler(**kwargs):
                    result = await mcp_client.call_tool(tool_name, kwargs)
                    return result.content
                return _mcp_handler

            # Asynchronous factory
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


# Global singleton tool registry
tool_registry = ToolRegistry()
