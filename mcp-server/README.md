# Enterprise MCP Server (Model Context Protocol)

Standalone Model Context Protocol (MCP) server providing enterprise tools, product data, customer lookups, and inventory status to autonomous AI agents over JSON-RPC 2.0.

## Protocol Capabilities
- **JSON-RPC 2.0**: Compatible with the official Anthropic / MCP specification (`tools/list`, `tools/call`, `initialize`, `ping`).
- **Domain Tools**:
  - `query_customer`: Search customer profiles by email or customer code.
  - `check_product_inventory`: Verify inventory stock, warehouse locations, and pricing.
  - `get_order_status`: Retrieve order fulfillment and tracking status.

## Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the MCP server on port 8001
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## Endpoints
- `GET /health`: Health and liveness probe.
- `GET /mcp/tools`: List all exposed enterprise tools.
- `POST /mcp`: JSON-RPC 2.0 protocol endpoint.
