from __future__ import annotations

from typing import Any

from auth.registry import get_provider
from logger import get_logger


class YouTubeClientError(Exception):
    pass


class MissingCredentialsError(YouTubeClientError):
    pass


class AuthenticationError(YouTubeClientError):
    pass


def get_youtube_client() -> Any:
    """
    Backwards-compatible YouTube client accessor.

    Delegates OAuth + token lifecycle to the auth provider layer so auth can
    become source-agnostic over time.
    """
    logger = get_logger(__name__)

    try:
        provider = get_provider("youtube")
        return provider.build_client()
    except Exception as e:
        # Preserve legacy exception shapes for existing callers
        msg = str(e)

        # Map provider errors into prior categories where possible
        from auth.errors import AuthInvalid

        if isinstance(e, AuthInvalid):
            logger.error(f"AuthenticationError: {msg}")
            raise AuthenticationError(msg) from e

        logger.error(f"YouTubeClientError: {msg}")
        raise YouTubeClientError(msg) from e
