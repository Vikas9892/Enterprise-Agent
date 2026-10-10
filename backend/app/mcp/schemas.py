"""Pydantic schemas for Model Context Protocol (MCP) and JSON-RPC 2.0."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class JSONRPCError(BaseModel):
    """Schema representing a JSON-RPC 2.0 error object."""

    code: int = Field(description="Error code indicating the error category")
    message: str = Field(description="Short human-readable description of the error")
    data: Optional[Any] = Field(default=None, description="Additional structured debugging details")


class JSONRPCRequest(BaseModel):
    """Schema representing an incoming JSON-RPC 2.0 request."""

    jsonrpc: str = Field(default="2.0", description="JSON-RPC protocol version")
    method: str = Field(description="Name of the protocol method being invoked")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Method parameter payload")
    id: Union[str, int] = Field(description="Unique request identifier")


class JSONRPCResponse(BaseModel):
    """Schema representing an outgoing JSON-RPC 2.0 response."""

    jsonrpc: str = Field(default="2.0", description="JSON-RPC protocol version")
    result: Optional[Any] = Field(default=None, description="Successful invocation result payload")
    error: Optional[JSONRPCError] = Field(default=None, description="Error payload if invocation failed")
    id: Optional[Union[str, int]] = Field(default=None, description="Matching request identifier")


class MCPTool(BaseModel):
    """Schema definition for an MCP tool discovered by the agent."""

    name: str = Field(description="Unique machine-readable tool identifier")
    description: str = Field(description="Clear explanation of the tool's purpose and functionality")
    input_schema: Dict[str, Any] = Field(
        default_factory=dict,
        alias="inputSchema",
        description="JSON Schema describing input parameter arguments",
    )


class MCPToolCall(BaseModel):
    """Payload representing a tool invocation request."""

    name: str = Field(description="Name of the tool to invoke")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Parameter arguments for execution")


class MCPToolResult(BaseModel):
    """Execution result returned by an MCP tool."""

    content: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Structured content items returned (text, resource, etc.)",
    )
    is_error: bool = Field(default=False, description="Whether execution ended in an error")


class MCPResource(BaseModel):
    """Schema describing an enterprise resource exposed through MCP."""

    uri: str = Field(description="Unique URI identifier for the resource")
    name: str = Field(description="User-friendly name of the resource")
    description: Optional[str] = Field(default=None, description="Resource summary")
    mime_type: Optional[str] = Field(default=None, description="MIME type indicator")
