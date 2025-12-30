from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol


class AuthHealthStatus(str, Enum):
    OK = "ok"
    OK_API_QUOTA = "ok_api_quota"
    AUTH_INVALID = "auth_invalid"
    FAILED = "failed"


@dataclass(frozen=True)
class AuthHealthResult:
    provider: str
    status: AuthHealthStatus
    message: str


class AuthProvider(Protocol):
    """
    Provider interface. Keep it minimal.

    - ensure_ready() may refresh tokens or prompt login (interactive)
    - build_client() returns an authenticated API client object for the provider
    - health_check() performs a cheap authenticated call to validate auth
    """

    name: str

    def ensure_ready(self) -> None: ...

    def build_client(self) -> Any: ...

    def health_check(self) -> AuthHealthResult: ...
