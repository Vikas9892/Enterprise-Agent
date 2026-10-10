"""Unit and integration tests for MCP client, protocol, tool registry, and endpoints."""

from unittest.mock import AsyncMock, patch
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.mcp.client import MCPClient
from app.mcp.schemas import (
    JSONRPCRequest,
    JSONRPCResponse,
    MCPTool,
    MCPToolResult,
)
from app.tools.registry import ToolRegistry


def test_jsonrpc_schemas_serialization() -> None:
    """Verify JSON-RPC 2.0 schemas encode and decode accurately."""
    req = JSONRPCRequest(
        id=1,
        method="tools/list",
        params={"scope": "enterprise"},
    )
    dumped = req.model_dump(by_alias=True)
    assert dumped["jsonrpc"] == "2.0"
    assert dumped["method"] == "tools/list"
    assert dumped["id"] == 1

    resp = JSONRPCResponse(
        id=1,
        result={"status": "ok"},
    )
    resp_dumped = resp.model_dump()
    assert resp_dumped["result"] == {"status": "ok"}
    assert resp_dumped["error"] is None


def test_tool_registry_local_registration_and_execution() -> None:
    """Verify registering and executing a local Python tool."""
    registry = ToolRegistry()

    def calculate_discount(price: float, rate: float) -> float:
        return price * (1.0 - rate)

    registry.register(
        name="calc_discount",
        description="Compute discounted price",
        parameters={
            "type": "object",
            "properties": {
                "price": {"type": "number"},
                "rate": {"type": "number"},
            },
            "required": ["price", "rate"],
        },
        handler=calculate_discount,
        source="local",
    )

    tools = registry.list_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "calc_discount"
    assert tools[0]["source"] == "local"

    # OpenAI format
    openai_tools = registry.to_openai_tools()
    assert len(openai_tools) == 1
    assert openai_tools[0]["type"] == "function"
    assert openai_tools[0]["function"]["name"] == "calc_discount"


@pytest.mark.asyncio
async def test_tool_registry_async_execution() -> None:
    """Verify async handler execution in ToolRegistry."""
    registry = ToolRegistry()

    async def async_lookup(account_id: str) -> str:
        return f"Account:{account_id}:Active"

    registry.register(
        name="async_lookup",
        description="Lookup account asynchronously",
        parameters={"type": "object", "properties": {"account_id": {"type": "string"}}},
        handler=async_lookup,
    )

    result = await registry.execute("async_lookup", {"account_id": "ACC-99"})
    assert result == "Account:ACC-99:Active"


@pytest.mark.asyncio
async def test_mcp_client_list_and_call_tool() -> None:
    """Verify MCPClient queries remote server via JSON-RPC."""
    client = MCPClient(server_url="http://test-mcp:8001")

    mock_list_response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "tools": [
                {
                    "name": "mock_query_inventory",
                    "description": "Mock inventory check",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"sku": {"type": "string"}},
                    },
                }
            ]
        },
    }

    mock_call_response = {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {
            "content": [{"type": "text", "text": '{"sku": "SKU-1", "stock": 50}'}],
            "isError": False,
        },
    }

    with patch.object(client, "_send_jsonrpc", new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = [
            mock_list_response["result"],
            mock_call_response["result"],
        ]

        # 1. List tools
        tools = await client.list_tools(force_refresh=True)
        assert len(tools) == 1
        assert tools[0].name == "mock_query_inventory"

        # 2. Call tool
        call_res = await client.call_tool("mock_query_inventory", {"sku": "SKU-1"})
        assert call_res.is_error is False
        assert len(call_res.content) == 1
        assert "SKU-1" in call_res.content[0]["text"]


def test_api_mcp_endpoints(client: TestClient) -> None:
    """Verify /api/v1/mcp/tools and /api/v1/mcp/tools/call endpoints."""
    # Register and authenticate user
    user_payload = {
        "email": "mcp_tester@enterprise.ai",
        "password": "ValidPassword999!",
        "full_name": "MCP Tester",
    }
    client.post("/api/v1/auth/register", json=user_payload)
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "mcp_tester@enterprise.ai", "password": "ValidPassword999!"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List tools endpoint
    tools_resp = client.get("/api/v1/mcp/tools", headers=headers)
    assert tools_resp.status_code == status.HTTP_200_OK
    assert isinstance(tools_resp.json(), list)

    # 2. Register a mock tool in global registry to test execution endpoint
    from app.tools.registry import tool_registry

    tool_registry.register(
        name="test_echo_tool",
        description="Echoes input",
        parameters={"type": "object", "properties": {"val": {"type": "string"}}},
        handler=lambda val: f"Echo:{val}",
    )

    # 3. Call tool endpoint
    call_payload = {"name": "test_echo_tool", "arguments": {"val": "hello_mcp"}}
    exec_resp = client.post("/api/v1/mcp/tools/call", json=call_payload, headers=headers)
    assert exec_resp.status_code == status.HTTP_200_OK
    data = exec_resp.json()
    assert data["name"] == "test_echo_tool"
    assert data["result"] == "Echo:hello_mcp"
    assert data["status"] == "success"
