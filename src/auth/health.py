from __future__ import annotations

from auth.base import AuthHealthResult
from auth.registry import get_provider


def check(provider_name: str = "youtube") -> AuthHealthResult:
    provider = get_provider(provider_name)
    return provider.health_check()
