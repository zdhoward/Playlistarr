from __future__ import annotations

from providers.base import MediaProvider
from providers.youtube.client import build_youtube_client
from providers.youtube.oauth_health_check import validate_oauth
from providers.youtube.api_manager import APIKeyManager
from providers.youtube.filters import filter_videos

from env import get_env


class YouTubeProvider(MediaProvider):
    name = "youtube"

    def __init__(self):
        self.env = get_env()
        self.api_keys = APIKeyManager(self.env.youtube_api_keys)
        self.youtube = build_youtube_client(self.api_keys)

    def validate_access(self) -> None:
        validate_oauth(self.youtube)

    def discover(self, artists_csv: str):
        """
        This intentionally delegates to existing discovery logic.
        No behavior change.
        """
        from stages.discover import discover_videos

        return discover_videos(
            youtube=self.youtube,
            artists_csv=artists_csv,
            country_code=self.env.country_code,
            force_update=self.env.force_update,
        )

    def sync(self, playlist_id: str, items):
        from stages.sync import sync_playlist

        sync_playlist(
            youtube=self.youtube,
            playlist_id=playlist_id,
            items=items,
            dry_run=self.env.dry_run,
            max_add=self.env.max_add,
            no_filter=self.env.no_filter,
        )
