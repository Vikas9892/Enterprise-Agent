"""Resilient exponential backoff with jitter and retry policy for LLM providers."""

import asyncio
import random
import time
from typing import Any, Callable, Coroutine, Optional, Set, Type, TypeVar
from app.core.logging import get_logger

logger = get_logger("app.llm.retry")

T = TypeVar("T")


def compute_backoff_delay(
    attempt: int,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
) -> float:
    """Calculate exponential backoff delay with randomized full jitter.

    Formula:
        base_delay = min(max_delay, initial_delay * (2 ** (attempt - 1)))
        delay = uniform(0, base_delay) if jitter else base_delay
    """
    if attempt <= 0:
        return 0.0

    exponential_delay = initial_delay * (2 ** (attempt - 1))
    capped_delay = min(max_delay, exponential_delay)

    if jitter:
        # Full jitter: randomized between initial_delay/2 and capped_delay
        delay = random.uniform(initial_delay * 0.5, capped_delay)
    else:
        delay = capped_delay

    return round(delay, 3)


def is_retryable_error(exc: Exception) -> bool:
    """Determine whether an exception is temporary and eligible for retry."""
    # Check status_code attribute common in HTTP & LLM SDK exceptions
    status_code = getattr(exc, "status_code", None)
    if status_code is not None:
        if status_code in (429, 500, 502, 503, 504):
            return True
        if 400 <= status_code < 500:
            return False

    error_name = exc.__class__.__name__.lower()
    error_message = str(exc).lower()

    # Rate limiting & timeout indicators
    retryable_patterns = (
        "ratelimit",
        "rate_limit",
        "timeout",
        "timed out",
        "connection",
        "serviceunavailable",
        "internalserver",
        "overloaded",
        "try again",
        "429",
        "502",
        "503",
        "504",
    )
    if any(pat in error_name or pat in error_message for pat in retryable_patterns):
        return True

    # Standard python network & timeout errors
    if isinstance(exc, (TimeoutError, ConnectionError, asyncio.TimeoutError)):
        return True

    return False


async def execute_with_retry(
    operation: Callable[..., Coroutine[Any, Any, T]],
    *args: Any,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
    operation_name: str = "LLM Call",
    **kwargs: Any,
) -> T:
    """Execute an asynchronous coroutine with exponential backoff and jitter."""
    attempt = 1
    last_exception: Optional[Exception] = None

    while attempt <= max_retries:
        try:
            return await operation(*args, **kwargs)
        except Exception as exc:
            last_exception = exc
            if not is_retryable_error(exc) or attempt == max_retries:
                logger.warning(
                    f"{operation_name} failed on attempt {attempt}/{max_retries}: {type(exc).__name__}: {str(exc)}",
                    extra={
                        "attempt": attempt,
                        "max_retries": max_retries,
                        "error": str(exc),
                        "retryable": is_retryable_error(exc),
                    },
                )
                raise exc

            delay = compute_backoff_delay(
                attempt=attempt,
                initial_delay=initial_delay,
                max_delay=max_delay,
                jitter=jitter,
            )
            logger.info(
                f"{operation_name} hit retryable error on attempt {attempt}/{max_retries}. Backing off for {delay:.2f}s: {str(exc)}",
                extra={
                    "attempt": attempt,
                    "max_retries": max_retries,
                    "backoff_delay": delay,
                    "error": str(exc),
                },
            )
            await asyncio.sleep(delay)
            attempt += 1

    if last_exception:
        raise last_exception
    raise RuntimeError(f"{operation_name} exceeded max retries")
