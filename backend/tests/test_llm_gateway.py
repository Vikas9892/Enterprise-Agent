"""Unit and integration tests for LLM Gateway, exponential backoff, and retries."""

from unittest.mock import AsyncMock, patch
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.auth.security import create_access_token
from app.core.config import Settings
from app.llm.gateway import LLMGateway
from app.llm.retry import compute_backoff_delay, execute_with_retry, is_retryable_error
from app.llm.schemas import ChatMessage, CompletionRequest


def test_compute_backoff_delay_exponential_growth() -> None:
    """Verify exponential delay increases monotonically without jitter."""
    d1 = compute_backoff_delay(attempt=1, initial_delay=1.0, max_delay=30.0, jitter=False)
    d2 = compute_backoff_delay(attempt=2, initial_delay=1.0, max_delay=30.0, jitter=False)
    d3 = compute_backoff_delay(attempt=3, initial_delay=1.0, max_delay=30.0, jitter=False)

    assert d1 == 1.0
    assert d2 == 2.0
    assert d3 == 4.0

    # Capped at max_delay
    d_max = compute_backoff_delay(attempt=10, initial_delay=1.0, max_delay=15.0, jitter=False)
    assert d_max == 15.0


def test_compute_backoff_delay_with_jitter() -> None:
    """Verify jitter produces positive randomized values within reasonable bounds."""
    for attempt in range(1, 5):
        delay = compute_backoff_delay(attempt=attempt, initial_delay=1.0, max_delay=20.0, jitter=True)
        assert delay > 0.0
        assert delay <= 20.0


def test_is_retryable_error() -> None:
    """Verify classification of transient vs non-transient exceptions."""
    class MockHttpError(Exception):
        def __init__(self, status_code: int):
            self.status_code = status_code

    assert is_retryable_error(MockHttpError(429)) is True
    assert is_retryable_error(MockHttpError(503)) is True
    assert is_retryable_error(MockHttpError(401)) is False
    assert is_retryable_error(MockHttpError(400)) is False

    assert is_retryable_error(TimeoutError("Connection timed out")) is True
    assert is_retryable_error(ConnectionError("Network disconnected")) is True
    assert is_retryable_error(ValueError("Invalid syntax")) is False


@pytest.mark.asyncio
async def test_execute_with_retry_eventual_success() -> None:
    """Verify execute_with_retry retries on failure and returns when successful."""
    call_count = 0

    async def flaky_call():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Temporary glitch")
        return "success"

    result = await execute_with_retry(
        flaky_call,
        max_retries=3,
        initial_delay=0.01,
        max_delay=0.1,
        jitter=False,
    )
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_execute_with_retry_exhaustion() -> None:
    """Verify execute_with_retry raises exception when all attempts fail."""
    async def always_fails():
        raise ConnectionError("Persistent network outage")

    with pytest.raises(ConnectionError):
        await execute_with_retry(
            always_fails,
            max_retries=2,
            initial_delay=0.01,
            max_delay=0.05,
            jitter=False,
        )


@pytest.mark.asyncio
async def test_llm_gateway_primary_completion() -> None:
    """Verify LLMGateway completes requests using primary model."""
    class MockChoice:
        message = type("Msg", (), {"content": "Hello! I am an Enterprise Agent."})()
        finish_reason = "stop"

    class MockResponse:
        id = "chatcmpl-test-123"
        choices = [MockChoice()]
        usage = type("Usage", (), {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18})()

    gateway = LLMGateway()
    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_litellm:
        mock_litellm.return_value = MockResponse()

        request = CompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="gpt-4o",
            temperature=0.1,
        )
        response = await gateway.complete(request)

        assert response.content == "Hello! I am an Enterprise Agent."
        assert response.model == "gpt-4o"
        assert response.fallback_triggered is False
        assert response.usage.total_tokens == 18


@pytest.mark.asyncio
async def test_llm_gateway_fallback_trigger() -> None:
    """Verify LLMGateway seamlessly switches to fallback model if primary fails."""
    class MockChoice:
        message = type("Msg", (), {"content": "Fallback response from Claude."})()
        finish_reason = "stop"

    class MockResponse:
        id = "chatcmpl-fallback-456"
        choices = [MockChoice()]
        usage = type("Usage", (), {"prompt_tokens": 12, "completion_tokens": 6, "total_tokens": 18})()

    test_settings = Settings(
        litellm_model="gpt-4o",
        llm_fallback_models=["claude-3-5-sonnet-20240620"],
        llm_max_retries=1,
        llm_retry_initial_delay=0.01,
    )
    gateway = LLMGateway(settings=test_settings)

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_litellm:
        # First model fails immediately, second model succeeds
        mock_litellm.side_effect = [
            ConnectionError("OpenAI API unreachable"),
            MockResponse(),
        ]

        request = CompletionRequest(
            messages=[ChatMessage(role="user", content="Test fallback")],
            model="gpt-4o",
            fallback_models=["claude-3-5-sonnet-20240620"],
        )
        response = await gateway.complete(request)

        assert response.content == "Fallback response from Claude."
        assert response.model == "claude-3-5-sonnet-20240620"
        assert response.fallback_triggered is True


def test_api_llm_complete_endpoint(client: TestClient) -> None:
    """Verify POST /api/v1/llm/complete endpoint with authentication."""
    class MockChoice:
        message = type("Msg", (), {"content": "Authenticated LLM response."})()
        finish_reason = "stop"

    class MockResponse:
        id = "cmpl-api-789"
        choices = [MockChoice()]
        usage = type("Usage", (), {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10})()

    # Register and authenticate a user
    user_payload = {
        "email": "llm_tester@enterprise.ai",
        "password": "ValidPassword999!",
        "full_name": "LLM Test User",
    }
    client.post("/api/v1/auth/register", json=user_payload)
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "llm_tester@enterprise.ai", "password": "ValidPassword999!"},
    )
    token = login_resp.json()["access_token"]

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_litellm:
        mock_litellm.return_value = MockResponse()

        payload = {
            "messages": [{"role": "user", "content": "Ping"}],
            "model": "gpt-4o",
        }
        resp = client.post(
            "/api/v1/llm/complete",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["content"] == "Authenticated LLM response."
        assert data["model"] == "gpt-4o"
