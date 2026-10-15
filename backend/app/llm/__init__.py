"""LLM gateway and resilient multi-provider routing package."""

from typing import Optional
from app.llm.gateway import LLMGateway
from app.llm.retry import compute_backoff_delay, execute_with_retry, is_retryable_error
from app.llm.schemas import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    StreamChunk,
    UsageInfo,
)

_gateway_instance: Optional[LLMGateway] = None


def get_llm_gateway() -> LLMGateway:
    """Return singleton instance of LLMGateway."""
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = LLMGateway()
    return _gateway_instance


__all__ = [
    "ChatMessage",
    "CompletionRequest",
    "CompletionResponse",
    "LLMGateway",
    "StreamChunk",
    "UsageInfo",
    "compute_backoff_delay",
    "execute_with_retry",
    "get_llm_gateway",
    "is_retryable_error",
]
