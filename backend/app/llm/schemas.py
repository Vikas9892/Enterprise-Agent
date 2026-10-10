"""Pydantic schemas for LLM completions, messages, and streaming."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Schema representing an individual message in a chat completion."""

    role: Literal["system", "user", "assistant", "tool"] = Field(
        description="Role of the message author"
    )
    content: str = Field(description="Text content of the message")
    name: Optional[str] = Field(default=None, description="Optional name identifier")


class CompletionRequest(BaseModel):
    """Request payload for LLM text completion generation."""

    messages: List[ChatMessage] = Field(
        min_length=1,
        description="Sequential list of conversational messages",
    )
    model: Optional[str] = Field(
        default=None,
        description="Target model name; falls back to configured default model",
    )
    fallback_models: Optional[List[str]] = Field(
        default=None,
        description="Ordered list of fallback models if primary model fails",
    )
    temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Sampling temperature controlling randomness",
    )
    max_tokens: Optional[int] = Field(
        default=2048,
        gt=0,
        description="Maximum tokens to generate",
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream partial message deltas",
    )


class UsageInfo(BaseModel):
    """Token consumption statistics for a completion request."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class CompletionResponse(BaseModel):
    """Response payload returned by the LLM Gateway."""

    id: str = Field(description="Unique completion execution ID")
    model: str = Field(description="Actual model that generated the completion")
    content: str = Field(description="Generated textual content")
    role: str = Field(default="assistant", description="Role of the responding agent")
    usage: UsageInfo = Field(default_factory=UsageInfo, description="Token usage details")
    finish_reason: Optional[str] = Field(default="stop", description="Reason completion finished")
    latency_seconds: float = Field(default=0.0, description="End-to-end response latency in seconds")
    fallback_triggered: bool = Field(
        default=False,
        description="Whether a fallback model was used due to primary model error",
    )


class StreamChunk(BaseModel):
    """Streaming chunk representing an incremental token delta."""

    delta: str = Field(description="Partial content delta chunk")
    model: str = Field(description="Model producing the stream")
    finish_reason: Optional[str] = Field(default=None, description="Finish reason if stream completed")
