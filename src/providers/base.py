from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Any


class MediaProvider(ABC):
    """
    Abstract interface for media providers (YouTube, Spotify, etc.)
    """

    name: str

    @abstractmethod
    def validate_access(self) -> None:
        """Verify credentials / API access."""
        raise NotImplementedError

    @abstractmethod
    def discover(self, artists_csv: str) -> Iterable[Any]:
        """Discover media items from an input source."""
        raise NotImplementedError

    @abstractmethod
    def sync(self, playlist_id: str, items: Iterable[Any]) -> None:
        """Apply discovered items to a playlist."""
        raise NotImplementedError
