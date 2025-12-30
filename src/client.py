"""
client.py

Shared YouTube Data API client builder.

Responsibilities:
- OAuth authentication
- Token refresh
- Token persistence
- YouTube API client construction

Does NOT:
- Perform discovery
- Modify playlists
- Contain hard-coded secrets
"""

from __future__ import annotations

import os
from typing import Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import config
from logger import init_logging, get_logger

# ----------------------------
# Logging
# ----------------------------
init_logging()
logger = get_logger(__name__)

from pathlib import Path

OAUTH_DIR = Path("../auth")
OAUTH_DIR.mkdir(exist_ok=True)

OAUTH_TOKEN_PATH = OAUTH_DIR / "oauth_token.json"
OAUTH_CLIENT_SECRET_PATH = OAUTH_DIR / "client_secret.json"

class YouTubeClientError(Exception):
    """Base exception for YouTube client errors."""

    pass


class MissingCredentialsError(YouTubeClientError):
    """Raised when OAuth credentials file is missing."""

    pass


class AuthenticationError(YouTubeClientError):
    """Raised when authentication fails."""

    pass


def get_youtube_client() -> Any:
    """
    Authenticate (or reuse cached credentials) and return
    an authorized YouTube Data API client.

    This is the ONLY place OAuth and client construction should occur.

    Returns:
        Authorized YouTube API client

    Raises:
        MissingCredentialsError: If OAuth credentials JSON is missing
        AuthenticationError: If authentication fails

    Examples:
        >>> youtube = get_youtube_client()
        >>> playlists = youtube.playlists().list(part='snippet', mine=True).execute()
    """
    creds: Optional[Credentials] = None

    # Ensure auth directory exists early
    os.makedirs(config.AUTH_DIR, exist_ok=True)

    # Load existing OAuth token if present
    if os.path.exists(config.OAUTH_TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(
                config.OAUTH_TOKEN_FILE,
                config.YOUTUBE_OAUTH_SCOPES,
            )
            logger.debug("Loaded existing OAuth credentials")
        except Exception as e:
            logger.warning(f"Failed to load existing credentials: {e}")
            creds = None

    # Refresh or re-auth if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.debug("Refreshing expired OAuth token...")
                creds.refresh(Request())
                logger.debug("Successfully refreshed OAuth token")
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                raise AuthenticationError(f"Token refresh failed: {e}") from e
        else:
            # Need fresh authentication
            if not os.path.exists(config.CLIENT_SECRETS_FILE):
                raise MissingCredentialsError(
                    f"Missing OAuth credentials JSON file: {config.CLIENT_SECRETS_FILE}\n"
                    "Create a Google Cloud OAuth Desktop App and download the JSON file.\n"
                    "Place it at: auth/client_secrets.json"
                )

            try:
                logger.debug("Starting OAuth authentication flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.CLIENT_SECRETS_FILE,
                    config.YOUTUBE_OAUTH_SCOPES,
                )
                creds = flow.run_local_server(port=0)
                logger.debug("Successfully authenticated with OAuth")
            except Exception as e:
                logger.error(f"OAuth authentication failed: {e}")
                raise AuthenticationError(f"OAuth flow failed: {e}") from e

        # Persist token
        try:
            with open(config.OAUTH_TOKEN_FILE, "w", encoding="utf-8") as token:
                token.write(creds.to_json())
            logger.debug(f"Saved OAuth token to {config.OAUTH_TOKEN_FILE}")
        except Exception as e:
            logger.warning(f"Failed to save OAuth token: {e}")

        # Best-effort permission tightening (POSIX only)
        try:
            os.chmod(config.OAUTH_TOKEN_FILE, 0o600)
            logger.debug("Set restrictive permissions on OAuth token file")
        except Exception as e:
            logger.debug(f"Could not set restrictive permissions: {e}")

    # Build and return YouTube client
    try:
        youtube_client = build("youtube", "v3", credentials=creds)
        logger.debug("Successfully built YouTube API client")
        return youtube_client
    except Exception as e:
        logger.error(f"Failed to build YouTube client: {e}")
        raise YouTubeClientError(f"Failed to build client: {e}") from e


# Export public API
__all__ = [
    "get_youtube_client",
    "YouTubeClientError",
    "MissingCredentialsError",
    "AuthenticationError",
]
