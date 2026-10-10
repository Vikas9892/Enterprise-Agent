"""Enterprise Model Context Protocol (MCP) server implementation."""

import json
from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(
    title="Enterprise MCP Server",
    version="0.1.0",
    description="Standalone Model Context Protocol server exposing enterprise domain tools.",
)

# Standard MCP Enterprise Tools Catalog
ENTERPRISE_TOOLS = [
    {
        "name": "query_customer",
        "description": "Look up enterprise customer profile and status by email or customer code.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Customer email or unique customer reference code",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "check_product_inventory",
        "description": "Check current available stock quantity, warehouse location, and pricing for a product SKU.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sku": {
                    "type": "string",
                    "description": "Product stock keeping unit identifier (e.g. SKU-ENTERPRISE-01)",
                }
            },
            "required": ["sku"],
        },
    },
    {
        "name": "get_order_status",
        "description": "Retrieve current tracking status, fulfillment state, and line items for an order.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "order_number": {
                    "type": "string",
                    "description": "Unique order reference number (e.g. ORD-2026-001)",
                }
            },
            "required": ["order_number"],
        },
    },
]


def _execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute enterprise mock tools returning structured MCP content."""
    if name == "query_customer":
        query = arguments.get("query", "").strip()
        data = {
            "customer_code": "CUST-1001",
            "name": "Acme Global Industries",
            "email": query if "@" in query else f"{query}@example.com",
            "tier": "Enterprise Tier 1",
            "status": "active",
            "assigned_rep": "Sarah Connor",
        }
        return {
            "content": [{"type": "text", "text": json.dumps(data)}],
            "isError": False,
        }

    elif name == "check_product_inventory":
        sku = arguments.get("sku", "").strip()
        data = {
            "sku": sku,
            "product_name": "Enterprise Cloud Appliance",
            "in_stock": True,
            "quantity_available": 142,
            "warehouse": "US-WEST-PRIMARY",
            "unit_price": 4999.00,
        }
        return {
            "content": [{"type": "text", "text": json.dumps(data)}],
            "isError": False,
        }

    elif name == "get_order_status":
        order_num = arguments.get("order_number", "").strip()
        data = {
            "order_number": order_num,
            "status": "processing",
            "carrier": "FedEx Express",
            "tracking_number": "TRK-9876543210",
            "estimated_delivery": "2026-10-15T18:00:00Z",
            "total_amount": 14997.00,
        }
        return {
            "content": [{"type": "text", "text": json.dumps(data)}],
            "isError": False,
        }

    else:
        return {
            "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
            "isError": True,
        }


@app.get("/health", tags=["Health"])
def health_check() -> Dict[str, str]:
    """Verify MCP server operational status."""
    return {
        "status": "healthy",
        "service": "enterprise-mcp-server",
        "version": "0.1.0",
    }


@app.get("/mcp/tools", tags=["MCP"])
def list_tools_http() -> Dict[str, Any]:
    """Direct HTTP helper returning registered tools."""
    return {"tools": ENTERPRISE_TOOLS}


@app.post("/mcp", tags=["MCP"])
def handle_jsonrpc(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Process JSON-RPC 2.0 protocol requests for MCP tool discovery and execution."""
    method = payload.get("method")
    req_id = payload.get("id")
    params = payload.get("params", {}) or {}

    if not method:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32600, "message": "Invalid Request: missing method"},
        }

    # Protocol handshake
    if method in ("initialize", "server/info"):
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "enterprise-mcp-server", "version": "0.1.0"},
            },
        }

    # Ping
    elif method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    # List Tools
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": ENTERPRISE_TOOLS},
        }

    # Call Tool
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        if not tool_name:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32602,
                    "message": "Invalid params: missing tool name",
                },
            }

        result = _execute_tool(tool_name, arguments)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result,
        }

    # Unknown method
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
