"""LiteLLM-based multi-provider gateway with automatic fallback and retries."""

import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional
import litellm

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.llm.retry import execute_with_retry
from app.llm.schemas import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    StreamChunk,
    UsageInfo,
)

logger = get_logger("app.llm.gateway")

# Configure litellm global defaults
litellm.drop_params = True
litellm.telemetry = False


class LLMGateway:
    """Enterprise multi-provider LLM gateway orchestrating retries and model fallbacks."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def _prepare_messages(self, messages: List[ChatMessage]) -> List[Dict[str, str]]:
        """Format domain ChatMessage list into OpenAI-compatible message dictionaries."""
        formatted = []
        for msg in messages:
            entry: Dict[str, str] = {"role": msg.role, "content": msg.content}
            if msg.name:
                entry["name"] = msg.name
            formatted.append(entry)
        return formatted

    async def _execute_single_model_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int],
    ) -> Any:
        """Call litellm async completion for a specific target model."""
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if self.settings.openai_api_key and "gpt" in model:
            kwargs["api_key"] = self.settings.openai_api_key
        if self.settings.anthropic_api_key and "claude" in model:
            kwargs["api_key"] = self.settings.anthropic_api_key

        return await litellm.acompletion(**kwargs)

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Generate a chat completion with retry resilience and fallback model traversal."""
        primary_model = request.model or self.settings.litellm_model
        fallback_models = (
            request.fallback_models
            if request.fallback_models is not None
            else self.settings.llm_fallback_models
        )
        if isinstance(fallback_models, str):
            fallback_models = [fallback_models]

        candidate_models = [primary_model] + [
            m for m in fallback_models if m != primary_model
        ]
        formatted_messages = self._prepare_messages(request.messages)

        start_time = time.perf_counter()
        last_error: Optional[Exception] = None

        for index, candidate_model in enumerate(candidate_models):
            is_fallback = index > 0
            if is_fallback:
                logger.warning(
                    f"Engaging fallback model '{candidate_model}' after primary model failure",
                    extra={
                        "primary_model": primary_model,
                        "fallback_model": candidate_model,
                        "attempted_candidates": candidate_models[:index],
                    },
                )

            try:
                response = await execute_with_retry(
                    self._execute_single_model_completion,
                    model=candidate_model,
                    messages=formatted_messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    max_retries=self.settings.llm_max_retries,
                    initial_delay=self.settings.llm_retry_initial_delay,
                    max_delay=self.settings.llm_retry_max_delay,
                    jitter=self.settings.llm_retry_jitter,
                    operation_name=f"LLM [{candidate_model}]",
                )

                latency = round(time.perf_counter() - start_time, 3)

                # Extract content from litellm response object
                choice = response.choices[0]
                content = choice.message.content or ""
                finish_reason = getattr(choice, "finish_reason", "stop")

                usage_data = getattr(response, "usage", None)
                usage = UsageInfo(
                    prompt_tokens=getattr(usage_data, "prompt_tokens", 0) if usage_data else 0,
                    completion_tokens=getattr(usage_data, "completion_tokens", 0) if usage_data else 0,
                    total_tokens=getattr(usage_data, "total_tokens", 0) if usage_data else 0,
                )

                return CompletionResponse(
                    id=getattr(response, "id", str(uuid.uuid4())),
                    model=candidate_model,
                    content=content,
                    role="assistant",
                    usage=usage,
                    finish_reason=finish_reason,
                    latency_seconds=latency,
                    fallback_triggered=is_fallback,
                )

            except Exception as exc:
                last_error = exc
                logger.error(
                    f"Model candidate '{candidate_model}' exhausted retries: {str(exc)}",
                    extra={"candidate_model": candidate_model, "error": str(exc)},
                )
                continue

        # If all candidates failed
        raise RuntimeError(
            f"All LLM model candidates ({candidate_models}) failed to respond. Last error: {str(last_error)}"
        ) from last_error

    async def stream(
        self, request: CompletionRequest
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream token deltas incrementally from the target LLM."""
        model = request.model or self.settings.litellm_model
        formatted_messages = self._prepare_messages(request.messages)

        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": formatted_messages,
            "temperature": request.temperature,
            "stream": True,
        }
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens

        stream_response = await litellm.acompletion(**kwargs)
        async for chunk in stream_response:
            choice = chunk.choices[0]
            delta = getattr(choice.delta, "content", "") or ""
            finish_reason = getattr(choice, "finish_reason", None)
            yield StreamChunk(
                delta=delta,
                model=model,
                finish_reason=finish_reason,
            )
