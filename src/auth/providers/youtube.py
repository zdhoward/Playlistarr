from __future__ import annotations

import os
from typing import Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import config
from auth.base import AuthHealthResult, AuthHealthStatus, AuthProvider
from auth.errors import AuthInvalid, AuthFailed
from logger import get_logger
from paths import AUTH_DIR, auth_client_secrets_file, auth_token_file


def _is_quota_exceeded_error(exc: Exception) -> bool:
    try:
        status = getattr(getattr(exc, "resp", None), "status", None)
        if status != 403:
            return False

        content = getattr(exc, "content", b"")
        if not content:
            return False

        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="ignore")

        return "quotaExceeded" in content
    except Exception:
        return False


class YouTubeOAuthProvider(AuthProvider):
    name = "youtube"

    def __init__(self) -> None:
        self._logger = get_logger("auth.youtube")

    def ensure_ready(self) -> None:
        """
        Ensures credentials exist and are valid (refresh if expired; interactive login if needed).
        Persists token to AUTH_DIR.
        """
        _ = self._load_or_authenticate()

    def build_client(self) -> Any:
        creds = self._load_or_authenticate()
        try:
            return build("youtube", "v3", credentials=creds)
        except Exception as e:
            self._logger.error(f"Failed to build YouTube client: {e}")
            raise AuthFailed(str(e)) from e

    def health_check(self) -> AuthHealthResult:
        """
        Validates OAuth by making a cheap authenticated request.
        Treats API quota exhaustion as OAuth OK.
        """
        self._logger.info("oauth.check.start")

        try:
            youtube = self.build_client()
            youtube.channels().list(part="id", mine=True, maxResults=1).execute()

            self._logger.info("oauth.check.ok")
            return AuthHealthResult(
                provider=self.name,
                status=AuthHealthStatus.OK,
                message="OAuth OK",
            )

        except Exception as e:
            if _is_quota_exceeded_error(e):
                self._logger.warning("oauth.check.ok_quota_exhausted")
                return AuthHealthResult(
                    provider=self.name,
                    status=AuthHealthStatus.OK_API_QUOTA,
                    message="OAuth OK (API quota exhausted)",
                )

            if isinstance(e, AuthInvalid):
                self._logger.error("oauth.check.auth_invalid", exc_info=e)
                return AuthHealthResult(
                    provider=self.name,
                    status=AuthHealthStatus.AUTH_INVALID,
                    message="OAuth INVALID – reauthentication required",
                )

            self._logger.error("oauth.check.failed", exc_info=e)
            return AuthHealthResult(
                provider=self.name,
                status=AuthHealthStatus.FAILED,
                message="OAuth check failed (unexpected error)",
            )

    # -----------------------------------------------------------------
    # Internals
    # -----------------------------------------------------------------

    def _load_or_authenticate(self) -> Credentials:
        AUTH_DIR.mkdir(parents=True, exist_ok=True)

        token_path = auth_token_file()
        secrets_path = auth_client_secrets_file()

        creds: Optional[Credentials] = None

        if token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    token_path,
                    config.YOUTUBE_OAUTH_SCOPES,
                )
                self._logger.debug("Loaded existing OAuth credentials")
            except Exception as e:
                self._logger.warning(f"Failed to load existing credentials: {e}")
                creds = None

        if creds and creds.valid:
            return creds

        if creds and creds.expired and creds.refresh_token:
            try:
                self._logger.debug("Refreshing expired OAuth token...")
                creds.refresh(Request())
                self._logger.debug("Successfully refreshed OAuth token")
                self._persist_token(token_path, creds)
                return creds
            except Exception as e:
                self._logger.error(f"Failed to refresh token: {e}")
                raise AuthInvalid(str(e)) from e

        if not secrets_path.exists():
            raise AuthInvalid(f"Missing OAuth credentials JSON file: {secrets_path}")

        try:
            self._logger.debug("Starting OAuth authentication flow...")
            flow = InstalledAppFlow.from_client_secrets_file(
                secrets_path,
                config.YOUTUBE_OAUTH_SCOPES,
            )
            creds = flow.run_local_server(port=0)
            self._logger.debug("Successfully authenticated with OAuth")
            self._persist_token(token_path, creds)
            return creds
        except Exception as e:
            self._logger.error(f"OAuth authentication failed: {e}")
            raise AuthInvalid(str(e)) from e

    def _persist_token(self, token_path: Any, creds: Credentials) -> None:
        try:
            token_path.write_text(creds.to_json(), encoding="utf-8")
            self._logger.debug("Saved OAuth token")
        except Exception:
            pass

        try:
            os.chmod(token_path, 0o600)
            self._logger.debug("Set restrictive permissions on OAuth token file")
        except Exception:
            pass
