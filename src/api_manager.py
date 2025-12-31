"""
api_manager.py

API key management and HTTP utilities.

Responsibilities:
- API key rotation for discovery
- OAuth quota tracking
- Retry logic with exponential backoff
- HTTP → domain error translation
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar

import requests
from googleapiclient.errors import HttpError

import config
from logger import get_logger


logger = get_logger(__name__)
T = TypeVar("T")

# ============================================================
# Global exhaustion flags
# ============================================================

_OAUTH_EXHAUSTED = False


def mark_api_keys_exhausted() -> None:
    os.environ["PLAYLISTARR_API_KEYS_EXHAUSTED"] = "1"


def api_keys_exhausted() -> bool:
    return os.environ.get("PLAYLISTARR_API_KEYS_EXHAUSTED") == "1"


def mark_oauth_exhausted() -> None:
    global _OAUTH_EXHAUSTED
    _OAUTH_EXHAUSTED = True


def oauth_exhausted() -> bool:
    return _OAUTH_EXHAUSTED


# ============================================================
# Exceptions
# ============================================================


class QuotaExhaustedError(Exception):
    """Raised when API key or OAuth quota is exhausted."""

    pass


class APIError(Exception):
    """Non-quota API failure."""

    pass


# ============================================================
# API Key Manager (Discovery)
# ============================================================


class APIKeyManager:
    def __init__(self, keys: List[str]):
        if not keys:
            raise ValueError("API keys list cannot be empty")

        self.keys = keys
        self.current_index = 0
        self.exhausted = False

        logger.debug(f"Initialized APIKeyManager with {len(keys)} keys")

    def current_key(self) -> str:
        if self.exhausted:
            raise QuotaExhaustedError("All API keys exhausted")
        return self.keys[self.current_index]

    def rotate(self) -> None:
        self.current_index += 1

        if self.current_index >= len(self.keys):
            self.exhausted = True
            mark_api_keys_exhausted()
            logger.warning("All API keys exhausted")
            raise QuotaExhaustedError("All API keys exhausted")

        logger.warning(f"Rotated to API key {self.current_index + 1}/{len(self.keys)}")

    @property
    def has_keys_remaining(self) -> bool:
        return not self.exhausted


# ============================================================
# Error detection helpers
# ============================================================


def _is_quota_payload(data: dict) -> bool:
    """
    YouTube quota errors are reliably signaled here:
    error.errors[].reason in ('quotaExceeded', 'dailyLimitExceeded')
    """
    try:
        for err in data.get("error", {}).get("errors", []):
            if err.get("reason") in ("quotaExceeded", "dailyLimitExceeded"):
                return True
    except Exception:
        pass
    return False


def is_quota_response(response: requests.Response) -> bool:
    if response.status_code != 403:
        return False
    try:
        return _is_quota_payload(response.json())
    except Exception:
        return False


def is_transient_status(status_code: int) -> bool:
    return status_code in (429, 500, 502, 503, 504)


def _classify_http_error(e: HttpError) -> str:
    """
    Returns: 'oauth_quota', 'auth', or 'other'
    """
    # First try structured error_details
    try:
        payload = e.error_details or {}
        if _is_quota_payload(payload):
            return "oauth_quota"
    except Exception:
        pass

    # Then try raw HTTP content (googleapiclient puts JSON here often)
    try:
        raw = (
            e.content.decode("utf-8", errors="ignore") if hasattr(e, "content") else ""
        )
        if "quota" in raw.lower() or "dailylimit" in raw.lower():
            return "oauth_quota"
    except Exception:
        pass

    # Auth failure
    if getattr(e, "status_code", None) == 401:
        return "auth"

    return "other"


# ============================================================
# Retry engine
# ============================================================


def oauth_tripwire():
    if oauth_exhausted():
        raise QuotaExhaustedError("OAuth quota exhausted")


def execute_with_retry(
    operation: Callable[[], T],
    name: str = "",
    **kwargs,  # ← swallow old callers
) -> T:
    # Accept legacy keyword
    if not name:
        name = kwargs.get("operation_name", "")

    last_exception: Optional[Exception] = None

    for attempt in range(config.MAX_RETRIES):
        try:
            return operation()

        except QuotaExhaustedError:
            # Hard stop - bubble up
            raise

        except HttpError as e:
            kind = _classify_http_error(e)

            if kind == "oauth_quota":
                logger.warning("OAuth quota exhausted")
                mark_oauth_exhausted()
                raise QuotaExhaustedError("OAuth quota exhausted") from e

            if kind == "auth":
                raise

            last_exception = e

        except Exception as e:
            last_exception = e

        if attempt == config.MAX_RETRIES - 1:
            break

        sleep_time = config.BACKOFF_BASE_SEC * (2**attempt)
        logger.warning(
            f"{name} failed (attempt {attempt + 1}/{config.MAX_RETRIES}), "
            f"retrying in {sleep_time}s: {last_exception}"
        )
        time.sleep(sleep_time)

    if last_exception:
        raise last_exception

    raise APIError("execute_with_retry failed")


# ============================================================
# HTTP JSON (Discovery)
# ============================================================


def http_get_json(
    url: str,
    params: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    api_key_manager: Optional[APIKeyManager] = None,
) -> Dict[str, Any]:

    def make_request() -> Dict[str, Any]:
        request_params = dict(params)

        if api_key_manager:
            request_params["key"] = api_key_manager.current_key()

        response = requests.get(
            url,
            params=request_params,
            headers=headers,
            timeout=timeout,
        )

        # API-key quota
        if is_quota_response(response):
            if not api_key_manager:
                raise QuotaExhaustedError("API quota exhausted")

            logger.warning("API key quota exhausted - rotating")
            api_key_manager.rotate()
            return make_request()

        if is_transient_status(response.status_code):
            raise APIError(f"Transient HTTP {response.status_code}")

        response.raise_for_status()

        # Keep the per-request sleep configurable at runtime.
        # Import lazily to avoid env construction / side-effects at import time.
        from env import get_env

        time.sleep(get_env().sleep_sec)
        return response.json()

    return execute_with_retry(make_request, "http_get_json")
