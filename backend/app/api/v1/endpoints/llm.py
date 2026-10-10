"""API endpoints for LLM text completions and streaming."""

import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.auth.dependencies import get_current_user
from app.database.models.user import User
from app.llm.gateway import LLMGateway
from app.llm.schemas import CompletionRequest, CompletionResponse

router = APIRouter()
gateway = LLMGateway()


@router.post(
    "/complete",
    response_model=CompletionResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate LLM completion",
    description="Generates an LLM response using resilient routing, retries, and automatic fallbacks.",
)
async def generate_completion(
    request: CompletionRequest,
    current_user: User = Depends(get_current_user),
) -> CompletionResponse:
    """Generate completion via the multi-provider LLM Gateway."""
    try:
        return await gateway.complete(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM generation failed: {str(exc)}",
        )


@router.post(
    "/stream",
    summary="Stream LLM completion",
    description="Streams completion tokens incrementally using Server-Sent Events (SSE).",
)
async def stream_completion(
    request: CompletionRequest,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Stream token deltas from the configured LLM provider."""
    async def event_generator():
        try:
            async for chunk in gateway.stream(request):
                payload = json.dumps({"delta": chunk.delta, "finish_reason": chunk.finish_reason})
                yield f"data: {payload}\n\n"
        except Exception as exc:
            err_payload = json.dumps({"error": str(exc)})
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
