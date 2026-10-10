"""Model Context Protocol (MCP) client communicating via JSON-RPC 2.0 over HTTP/SSE."""

from typing import Any, Dict, List, Optional
import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.mcp.schemas import (
    JSONRPCRequest,
    JSONRPCResponse,
    MCPTool,
    MCPToolResult,
)

logger = get_logger("app.mcp.client")


class MCPClient:
    """Client for discovering enterprise tools and executing invocations on MCP servers."""

    def __init__(self, server_url: Optional[str] = None) -> None:
        settings = get_settings()
        self.server_url = (server_url or settings.mcp_server_url).rstrip("/")
        self.endpoint = f"{self.server_url}/mcp"
        self._cached_tools: List[MCPTool] = []
        self._request_counter = 0

    def _next_request_id(self) -> int:
        self._request_counter += 1
        return self._request_counter

    async def ping(self) -> bool:
        """Verify network connectivity and health of the target MCP server."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.server_url}/health")
                return resp.status_code == 200
        except Exception:
            return False

    async def _send_jsonrpc(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Dispatch a JSON-RPC 2.0 payload to the remote MCP server endpoint."""
        req_id = self._next_request_id()
        payload = JSONRPCRequest(
            id=req_id,
            method=method,
            params=params or {},
        ).model_dump(by_alias=True)

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(self.endpoint, json=payload)
            resp.raise_for_status()
            data = resp.json()

        rpc_resp = JSONRPCResponse.model_validate(data)
        if rpc_resp.error:
            raise RuntimeError(
                f"MCP JSON-RPC error ({rpc_resp.error.code}): {rpc_resp.error.message}"
            )
        return rpc_resp.result or {}

    async def list_tools(self, force_refresh: bool = False) -> List[MCPTool]:
        """Discover available tools registered on the MCP server."""
        if self._cached_tools and not force_refresh:
            return self._cached_tools

        try:
            result = await self._send_jsonrpc("tools/list")
            tools_raw = result.get("tools", [])
            tools = [MCPTool.model_validate(t) for t in tools_raw]
            self._cached_tools = tools
            logger.info(
                f"Successfully discovered {len(tools)} tools from MCP server at {self.server_url}",
                extra={"tool_count": len(tools), "server_url": self.server_url},
            )
            return tools
        except Exception as exc:
            logger.warning(
                f"Failed to query MCP tools from {self.server_url}: {str(exc)}",
                extra={"server_url": self.server_url, "error": str(exc)},
            )
            return self._cached_tools

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """Invoke an MCP tool with provided argument parameters."""
        logger.info(
            f"Invoking remote MCP tool '{name}'",
            extra={"tool_name": name, "arguments": arguments},
        )
        params = {"name": name, "arguments": arguments}
        result = await self._send_jsonrpc("tools/call", params)

        content = result.get("content", [])
        is_error = result.get("isError", False)

        return MCPToolResult(
            content=content,
            is_error=is_error,
        )
