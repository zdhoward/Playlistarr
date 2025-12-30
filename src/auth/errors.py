from __future__ import annotations


class AuthError(Exception):
    """Base auth error for any provider."""


class AuthInvalid(AuthError):
    """Credentials are missing/invalid or interactive reauth required."""


class AuthFailed(AuthError):
    """Unexpected auth failure."""
