#!/usr/bin/env python3
"""
oauth_health_check.py

Fast, zero-side-effect OAuth validator.

- Auto-deletes and refreshes invalid OAuth tokens
- Ignores quota exhaustion
"""

import sys
import json
from pathlib import Path
from googleapiclient.errors import HttpError

from client import get_youtube_client, AuthenticationError, OAUTH_TOKEN_PATH
from logger import init_logging, get_logger

from api_manager import oauth_tripwire

init_logging()
logger = get_logger(__name__)


def _parse_error(e: HttpError) -> dict:
    try:
        return json.loads(e.content.decode("utf-8"))
    except Exception:
        return {}


def is_auth_error(e: HttpError) -> bool:
    if e.resp.status == 401:
        return True

    data = _parse_error(e)
    for err in data.get("error", {}).get("errors", []):
        if err.get("reason") in (
            "authError",
            "invalidCredentials",
            "tokenExpired",
            "keyInvalid",
        ):
            return True
    return False


def is_quota_error(e: HttpError) -> bool:
    if e.resp.status != 403:
        return False

    data = _parse_error(e)
    for err in data.get("error", {}).get("errors", []):
        if err.get("reason") in (
            "quotaExceeded",
            "dailyLimitExceeded",
            "userRateLimitExceeded",
        ):
            return True
    return False


def _delete_token():
    if OAUTH_TOKEN_PATH.exists():
        logger.warning("Deleting invalid OAuth token")
        OAUTH_TOKEN_PATH.unlink(missing_ok=True)


def _cheap_oauth_test(yt):
    oauth_tripwire()
    yt.playlists().list(
        part="id",
        mine=True,
        maxResults=1,
    ).execute()


def main() -> int:
    try:
        yt = get_youtube_client()
        _cheap_oauth_test(yt)
        logger.debug("OAuth OK")
        return 0

    except HttpError as e:
        if is_quota_error(e):
            logger.warning("OAuth valid but quota exhausted")
            return 0

        if is_auth_error(e):
            logger.warning("OAuth token invalid or expired — reauth required")
            _delete_token()

            # Try once more to trigger reauth
            try:
                yt = get_youtube_client()
                _cheap_oauth_test(yt)
                logger.debug("OAuth refreshed successfully")
                return 0
            except Exception:
                logger.error("Reauthentication failed")
                return 2

        logger.error("YouTube API error:")
        logger.error(e)
        return 3

    except AuthenticationError as e:
        logger.warning("OAuth auth error — reauth required")
        _delete_token()
        return 2

    except Exception:
        logger.exception("Unexpected OAuth failure")
        return 4


if __name__ == "__main__":
    sys.exit(main())
