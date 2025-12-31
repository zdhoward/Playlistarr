from __future__ import annotations

import sys

from auth.health import check
from auth.errors import AuthError
from auth.base import AuthHealthStatus
from logger import get_logger


def main() -> int:
    """
    OAuth health check entrypoint.

    This is a thin compatibility wrapper used by the sync workflow.
    All real logic is delegated to the auth provider system.

    Exit codes:
        0  -> OK or quota exhausted
        2  -> OAuth credentials invalid
        3  -> Unexpected auth failure
    """
    logger = get_logger(__name__)

    try:
        result = check(provider_name="youtube")
    except AuthError as e:
        logger.error("oauth.health.error", exc_info=e)
        return 3
    except Exception as e:
        logger.exception("oauth.health.unexpected_error")
        return 3

    if result.status is AuthHealthStatus.OK:
        logger.info("oauth.health.ok")
        return 0

    if result.status is AuthHealthStatus.QUOTA_EXHAUSTED:
        logger.warning("oauth.health.quota_exhausted")
        return 0

    if result.status is AuthHealthStatus.INVALID:
        logger.error("oauth.health.invalid")
        return 2

    # Defensive fallback
    logger.error("oauth.health.unknown_status", extra={"status": result.status})
    return 3


if __name__ == "__main__":
    sys.exit(main())
