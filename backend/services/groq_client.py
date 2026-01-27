"""
Centralized Groq model routing and fallback.

CORE GOAL:
- Choose the best available model for each request
- Automatically fall back on rate limits or temporary errors
- Never change higher-level behavior or response formats

This module is intentionally small and generic so it can be reused by:
- services.query_generation (SQL generation)
- services.intent_generation (if used)
- services.ai_formatter (post-execution phrasing)
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

from groq import Groq

logger = logging.getLogger(__name__)


# === Model Priority Configuration ===

PRIMARY_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODELS: List[str] = [
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
]

MODEL_PRIORITY: List[str] = [PRIMARY_MODEL] + FALLBACK_MODELS

# Cooldown state: model_name -> unix timestamp until which the model is considered unavailable
_model_cooldowns: Dict[str, float] = {name: 0.0 for name in MODEL_PRIORITY}


def _now() -> float:
    return time.time()


def _is_in_cooldown(model: str, now: Optional[float] = None) -> bool:
    if now is None:
        now = _now()
    return _model_cooldowns.get(model, 0.0) > now


def _mark_unavailable(model: str, cooldown_seconds: int = 90) -> None:
    """Mark a model as temporarily unavailable (rate-limited / 503)."""
    until = _now() + cooldown_seconds
    _model_cooldowns[model] = until
    logger.warning("Model %s marked unavailable until %s", model, time.strftime("%H:%M:%S", time.localtime(until)))


def _is_rate_limit_or_unavailable_error(exc: Exception) -> bool:
    """
    Heuristic to detect temporary availability issues (rate limits / 503).

    We intentionally avoid depending on specific Groq error types so this
    remains robust across library versions.
    """
    text = str(exc).lower()

    # Common signals for rate limiting / temporary failure
    if "rate limit" in text or "quota" in text:
        return True

    # Look for HTTP status codes in the message
    if "429" in text or "status 429" in text:
        return True
    if "503" in text or "status 503" in text or "service unavailable" in text:
        return True

    # Some Groq errors expose status/status_code attributes
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if isinstance(status, int) and status in (429, 503):
        return True

    return False


def get_groq_client() -> Optional[Groq]:
    """
    Return a shared Groq client instance, or None if no API key is configured.

    This is a convenience for code paths that don't already manage their own client.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY not set - Groq client unavailable")
        return None

    # Simple module-level singleton
    global _shared_client  # type: ignore[assignment]
    try:
        client: Groq = _shared_client  # type: ignore[name-defined]
    except NameError:
        _shared_client = Groq(api_key=api_key)  # type: ignore[assignment]
        client = _shared_client  # type: ignore[assignment]

    return client


def call_with_fallback(
    client: Groq,
    *,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
    timeout_seconds: Optional[float] = None,
) -> Any:
    """
    Call Groq chat.completions.create with automatic model fallback.

    BEHAVIOR:
    - Try models in MODEL_PRIORITY order, skipping those in cooldown.
    - On rate limit / temporary errors (429/503), mark model in cooldown and try the next.
    - On non-temporary errors, re-raise immediately (preserves existing behavior).
    - If all models fail, re-raise the last error so callers can map it to their
      existing user-facing messages.
    """
    now = _now()
    available_models = [m for m in MODEL_PRIORITY if not _is_in_cooldown(m, now)]

    # If everything is in cooldown, allow trying the primary again after cooldown expiry.
    if not available_models:
        # Find earliest cooldown expiry and, if already passed, clear it for primary.
        earliest = min(_model_cooldowns.values() or [0.0])
        if earliest <= now:
            available_models = MODEL_PRIORITY[:]
        else:
            # Still within global cooldown; we'll still try in priority order and let
            # the existing error handling surface.
            available_models = MODEL_PRIORITY[:]

    last_error: Optional[Exception] = None

    for model in available_models:
        try:
            logger.info("Calling Groq model: %s", model)
            kwargs: Dict[str, Any] = dict(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if timeout_seconds is not None:
                # Use Groq client's with_options to set timeout if requested
                response = client.with_options(timeout=timeout_seconds).chat.completions.create(**kwargs)
            else:
                response = client.chat.completions.create(**kwargs)
            return response

        except Exception as exc:  # noqa: BLE001 - we intentionally handle all errors here
            last_error = exc
            if _is_rate_limit_or_unavailable_error(exc):
                _mark_unavailable(model)
                # Try the next model in the list
                continue

            # For non-temporary errors, preserve existing behavior: re-raise immediately
            logger.error("Groq call failed for model %s: %s", model, exc)
            raise

    # If we reach here, all models failed (likely due to rate limits / temporary issues).
    if last_error is not None:
        logger.error("All Groq models failed due to temporary errors: %s", last_error)
        # Re-raise so existing callers can map to their generic retry messages.
        raise last_error

    # Extremely unlikely: no models and no error – raise a generic error.
    raise RuntimeError("No Groq models available for request")



