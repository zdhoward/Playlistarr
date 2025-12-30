from __future__ import annotations

from typing import Dict

from auth.base import AuthProvider
from auth.providers.youtube import YouTubeOAuthProvider


_PROVIDERS: Dict[str, AuthProvider] = {
    "youtube": YouTubeOAuthProvider(),
}


def get_provider(name: str) -> AuthProvider:
    key = (name or "").strip().lower()
    if key not in _PROVIDERS:
        raise ValueError(f"Unknown auth provider: {name}")
    return _PROVIDERS[key]
