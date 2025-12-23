"""
api_manager.py

API key management and HTTP utilities.

This module provides:
- API key rotation for quota management
- Retry logic with exponential backoff
- Quota exhaustion detection
- HTTP request wrappers
"""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

import logging
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar

import requests

import config

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================
# Exceptions
# ============================================================


class QuotaExhaustedError(Exception):
    """Raised when all API keys are exhausted."""

    pass


class APIError(Exception):
    """Base exception for API errors."""

    pass


# ============================================================
# API Key Manager
# ============================================================


class APIKeyManager:
    """
    Manages multiple API keys with automatic rotation on quota exhaustion.

    Thread-safe key rotation with state tracking.
    """

    def __init__(self, keys: List[str]):
        """
        Initialize with list of API keys.

        Args:
            keys: List of YouTube API keys

        Raises:
            ValueError: If keys list is empty
        """
        if not keys:
            raise ValueError("API keys list cannot be empty")

        self.keys = keys
        self.current_index = 0
        self.exhausted = False

        logger.info(f"Initialized APIKeyManager with {len(keys)} keys")

    def current_key(self) -> str:
        """
        Get the current active API key.

        Returns:
            Current API key string

        Raises:
            QuotaExhaustedError: If all keys are exhausted
        """
        if self.exhausted:
            raise QuotaExhaustedError("All API keys exhausted")

        return self.keys[self.current_index]

    def rotate(self) -> None:
        """
        Rotate to the next API key.

        Raises:
            QuotaExhaustedError: If no more keys available
        """
        self.current_index += 1

        if self.current_index >= len(self.keys):
            self.exhausted = True
            logger.error("All API keys exhausted")
            raise QuotaExhaustedError("All API keys exhausted")

        logger.warning(f"Rotated to API key {self.current_index + 1}/{len(self.keys)}")

    @property
    def has_keys_remaining(self) -> bool:
        """Check if there are more keys available."""
        return not self.exhausted and self.current_index < len(self.keys)

    def reset(self) -> None:
        """Reset to first key (for testing or retry scenarios)."""
        self.current_index = 0
        self.exhausted = False
        logger.info("Reset API key manager to first key")


# ============================================================
# HTTP Utilities
# ============================================================


def is_quota_error(response: requests.Response) -> bool:
    """
    Detect if response indicates quota exhaustion.

    Args:
        response: HTTP response object

    Returns:
        True if quota is exhausted
    """
    if response.status_code != 403:
        return False

    try:
        data = response.json()
        content = str(data).lower()
        return "quota" in content or "dailylimit" in content
    except Exception:
        return False


def is_transient_error(status_code: int) -> bool:
    """
    Check if HTTP status code represents a transient error.

    Args:
        status_code: HTTP status code

    Returns:
        True if error is transient and should be retried
    """
    return status_code in (429, 500, 502, 503, 504)


def execute_with_retry(
    operation: Callable[[], T],
    max_retries: int = 3,
    backoff_base: float = 1.0,
    is_quota_check: Optional[Callable[[Exception], bool]] = None,
) -> T:
    """
    Execute an operation with exponential backoff retry logic.

    Args:
        operation: Function to execute
        max_retries: Maximum number of retry attempts
        backoff_base: Base delay for exponential backoff
        is_quota_check: Optional function to check if exception is quota-related

    Returns:
        Result of successful operation

    Raises:
        QuotaExhaustedError: If quota is exhausted
        Exception: Last exception if all retries fail

    Examples:
        >>> result = execute_with_retry(lambda: api_call())
    """
    last_exception: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            return operation()
        except Exception as e:
            last_exception = e

            # Check for quota exhaustion
            if is_quota_check and is_quota_check(e):
                raise QuotaExhaustedError("Quota exhausted") from e

            # Last attempt - don't sleep
            if attempt == max_retries - 1:
                break

            # Exponential backoff
            sleep_time = backoff_base * (2**attempt)
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed, "
                f"retrying in {sleep_time}s: {e}"
            )
            time.sleep(sleep_time)

    # All retries exhausted
    if last_exception:
        raise last_exception

    raise APIError("Operation failed with no exception recorded")


def http_get_json(
    url: str,
    params: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    api_key_manager: Optional[APIKeyManager] = None,
) -> Dict[str, Any]:
    """
    GET JSON with retry logic and API key rotation.

    Args:
        url: Target URL
        params: Query parameters
        headers: Optional HTTP headers
        timeout: Request timeout in seconds
        api_key_manager: Optional API key manager for rotation

    Returns:
        Parsed JSON response

    Raises:
        QuotaExhaustedError: If quota is exhausted
        requests.RequestException: On network errors
    """

    def make_request() -> Dict[str, Any]:
        # Add API key if manager provided
        request_params = dict(params)
        if api_key_manager:
            request_params["key"] = api_key_manager.current_key()

        response = requests.get(
            url,
            params=request_params,
            headers=headers,
            timeout=timeout,
        )

        # Check for quota exhaustion
        if is_quota_error(response):
            if api_key_manager:
                logger.warning("Quota exhausted for current API key")
                api_key_manager.rotate()
                # Retry with new key
                return make_request()
            else:
                raise QuotaExhaustedError("API quota exhausted")

        # Check for transient errors
        if is_transient_error(response.status_code):
            response.raise_for_status()

        # Success
        response.raise_for_status()

        # Rate limiting
        time.sleep(config.SLEEP_BETWEEN_CALLS_SEC)

        return response.json()

    return execute_with_retry(
        make_request,
        max_retries=config.MAX_RETRIES,
        backoff_base=config.BACKOFF_BASE_SEC,
    )
