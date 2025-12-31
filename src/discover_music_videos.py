#!/usr/bin/env python3
"""
discover_music_videos.py

Discovers official music videos for artists from a CSV file.

This script:
- Resolves artist channels (VEVO, official channels)
- Discovers videos from channel uploads
- Classifies videos using semantic filters
- Handles quota exhaustion gracefully
- Maintains resumable state

Does NOT:
- Modify playlists
- Perform OAuth operations
- Download videos
"""

from __future__ import annotations

from env import get_env

import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import isodate
import requests

import config
import filters
from api_manager import APIKeyManager, QuotaExhaustedError, http_get_json
from utils import discovery_output_path, read_json_safe, write_json
from logger import init_logging, get_logger
from ui.events import emit_ui_event

# ----------------------------
# Logging
# ----------------------------
init_logging()
logger = get_logger(__name__)

# ============================================================
# Data Classes
# ============================================================


@dataclass
class VideoEntry:
    """Represents a discovered video with metadata."""

    video_id: str
    title: str
    description: str
    published_at: str
    published_year: int
    channel_title: str
    duration: int
    definition: str
    url: str
    reason: str = ""
    retries: int = 0
    geo_blocked_here: bool = False
    playable: bool = True
    source: str = "original"
    original_video_id: Optional[str] = None
    original_url: Optional[str] = None
    fallback_query: Optional[str] = None
    fallback_score: Optional[int] = None


@dataclass
class ChannelInfo:
    """Channel metadata."""

    channel_id: str
    channel_title: str
    channel_url: str
    is_vevo: bool
    is_topic: bool
    is_official_artist: bool


@dataclass
class DiscoveryStats:
    """Statistics for a discovery run."""

    artist: str
    accepted: int = 0
    review: int = 0
    failed: int = 0
    channel: Optional[ChannelInfo] = None
    matched_via: str = "none"


@dataclass
class ArtistState:
    """State tracking for an artist's discovery process."""

    channel: Optional[Dict[str, Any]] = None
    processed: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    completed: bool = False
    last_run: Optional[str] = None
    last_completed: Optional[str] = None


# ============================================================
# Utilities
# ============================================================


def now_utc() -> str:
    """Get current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def read_artists_csv(csv_path: Path) -> List[str]:
    """
    Read artist names from CSV file.

    Args:
        csv_path: Path to CSV file

    Returns:
        List of artist names
    """
    artists = []

    with csv_path.open("r", encoding="utf-8") as f:
        for line in f:
            artist = line.strip()

            # Skip empty lines and header
            if not artist or artist.lower() == "artist":
                continue

            artists.append(artist)

    logger.debug(f"Loaded {len(artists)} artists from {csv_path}")
    return artists


def normalize_title_for_search(title: str) -> str:
    """
    Normalize title for search queries by removing common suffixes.

    Args:
        title: Video title

    Returns:
        Normalized title
    """
    t = title

    # Remove bracketed/parenthetical content
    t = re.sub(r"\[[^\]]*\]", " ", t)
    t = re.sub(r"\([^\)]*\)", " ", t)

    # Remove common suffixes
    t = re.sub(r"\bofficial music video\b", " ", t, flags=re.I)
    t = re.sub(r"\bofficial video\b", " ", t, flags=re.I)
    t = re.sub(r"\bmusic video\b", " ", t, flags=re.I)
    t = re.sub(r"\bhd\b", " ", t, flags=re.I)
    t = re.sub(r"\b4k\b", " ", t, flags=re.I)

    # Collapse whitespace
    t = re.sub(r"\s+", " ", t).strip()
    return t


def parse_duration_seconds(iso_duration: str) -> int:
    """
    Parse ISO 8601 duration to seconds.

    Args:
        iso_duration: ISO duration string (e.g., "PT3M45S")

    Returns:
        Duration in seconds
    """
    try:
        return int(isodate.parse_duration(iso_duration).total_seconds())
    except Exception as e:
        logger.warning(f"Failed to parse duration '{iso_duration}': {e}")
        return 0


# ============================================================
# YouTube API Wrappers
# ============================================================


class YouTubeAPI:
    """YouTube Data API wrapper with quota management."""

    def __init__(self, api_key_manager: APIKeyManager):
        """
        Initialize YouTube API wrapper.

        Args:
            api_key_manager: API key manager for quota handling
        """
        self.api_key_manager = api_key_manager

    def _get(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute YouTube API GET request with quota handling."""
        return http_get_json(
            url,
            params,
            timeout=config.REQUEST_TIMEOUT,
            api_key_manager=self.api_key_manager,
        )

    def get_channel_by_id(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Get channel details by ID.

        Args:
            channel_id: YouTube channel ID

        Returns:
            Channel data or None if not found
        """
        try:
            data = self._get(
                config.CHANNELS_URL,
                {"part": "snippet,contentDetails", "id": channel_id},
            )
            items = data.get("items", [])
            return items[0] if items else None
        except QuotaExhaustedError:
            raise
        except Exception as e:
            logger.warning(f"Failed to get channel {channel_id}: {e}")
            return None

    def get_channel_id_from_username(self, username: str) -> Optional[str]:
        """
        Get channel ID from username.

        Args:
            username: YouTube username

        Returns:
            Channel ID or None if not found
        """
        try:
            data = self._get(
                config.CHANNELS_URL, {"part": "id", "forUsername": username}
            )
            items = data.get("items", [])
            return items[0].get("id") if items else None
        except QuotaExhaustedError:
            raise
        except Exception as e:
            logger.warning(f"Failed to get channel ID for username {username}: {e}")
            return None

    def search_channels(self, query: str, max_results: int = 5) -> List[str]:
        """
        Search for channels by query.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of channel IDs
        """
        try:
            data = self._get(
                config.SEARCH_URL,
                {
                    "part": "snippet",
                    "q": query,
                    "type": "channel",
                    "maxResults": max_results,
                },
            )

            channel_ids = []
            for item in data.get("items", []):
                cid = item.get("id", {}).get("channelId")
                if cid:
                    channel_ids.append(cid)

            return channel_ids
        except QuotaExhaustedError:
            raise
        except Exception as e:
            logger.warning(f"Failed to search channels for '{query}': {e}")
            return []

    def search_channel_videos(
        self,
        query: str,
        channel_id: Optional[str] = None,
        max_results: int = 25,
    ) -> List[Dict[str, Any]]:
        try:
            params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": max_results,
            }

            if channel_id:
                params["channelId"] = channel_id

            data = self._get(config.SEARCH_URL, params)

            videos = []
            for item in data.get("items", []):
                vid = item.get("id", {}).get("videoId")
                if not vid:
                    continue

                snippet = item.get("snippet", {})
                videos.append(
                    {
                        "video_id": vid,
                        "title": snippet.get("title", ""),
                        "description": snippet.get("description", ""),
                        "published_at": snippet.get("publishedAt", ""),
                        "channel_title": snippet.get("channelTitle", ""),
                    }
                )

            return videos
        except QuotaExhaustedError:
            raise
        except Exception as e:
            logger.warning(f"Search failed for '{query}': {e}")
            return []

    def get_uploads_playlist_id(self, channel_id: str) -> Optional[str]:
        """
        Get the uploads playlist ID for a channel.

        Args:
            channel_id: YouTube channel ID

        Returns:
            Uploads playlist ID or None
        """
        channel = self.get_channel_by_id(channel_id)
        if not channel:
            return None

        content_details = channel.get("contentDetails", {})
        related = content_details.get("relatedPlaylists", {})
        return related.get("uploads")

    def list_uploads(self, channel_id: str) -> List[Dict[str, Any]]:
        """
        List all videos from channel's uploads playlist.

        Args:
            channel_id: YouTube channel ID

        Returns:
            List of video metadata dictionaries
        """
        uploads_playlist_id = self.get_uploads_playlist_id(channel_id)
        if not uploads_playlist_id:
            logger.warning(f"No uploads playlist for channel {channel_id}")
            return []

        videos = []
        page_token = None

        while True:
            try:
                params = {
                    "part": "snippet,contentDetails",
                    "playlistId": uploads_playlist_id,
                    "maxResults": 50,
                }
                if page_token:
                    params["pageToken"] = page_token

                data = self._get(config.PLAYLIST_ITEMS_URL, params)

                for item in data.get("items", []):
                    content_details = item.get("contentDetails", {})
                    snippet = item.get("snippet", {})
                    video_id = content_details.get("videoId")

                    if not video_id:
                        continue

                    videos.append(
                        {
                            "video_id": video_id,
                            "title": snippet.get("title", ""),
                            "description": snippet.get("description", ""),
                            "published_at": snippet.get("publishedAt", ""),
                            "channel_title": snippet.get("channelTitle", ""),
                        }
                    )

                page_token = data.get("nextPageToken")
                if not page_token:
                    break

            except requests.HTTPError as e:
                if e.response and e.response.status_code == 404:
                    logger.warning(
                        f"Uploads playlist not found for channel {channel_id}"
                    )
                    return videos
                raise

        logger.debug(f"Found {len(videos)} videos in channel {channel_id}")
        return videos

    def get_video_details(self, video_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get details for multiple videos (batched).

        Args:
            video_ids: List of video IDs

        Returns:
            Dictionary mapping video_id to details
        """
        details = {}

        # Batch in groups of 50
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i : i + 50]

            try:
                data = self._get(
                    config.VIDEOS_URL,
                    {"part": "contentDetails,status", "id": ",".join(batch)},
                )

                for item in data.get("items", []):
                    details[item["id"]] = item

            except QuotaExhaustedError:
                raise
            except Exception as e:
                logger.warning(f"Failed to get video details for batch: {e}")

        return details


# ============================================================
# Video Classification
# ============================================================


def is_video_playable(video_detail: Dict[str, Any]) -> bool:
    """Check if video is publicly playable."""
    status = video_detail.get("status", {})
    privacy = status.get("privacyStatus")
    upload_status = status.get("uploadStatus")

    if upload_status and upload_status != "processed":
        return False
    if privacy and privacy != "public":
        return False

    return True


def is_video_blocked(video_detail: Dict[str, Any], country: str) -> bool:
    """Check if video is geo-blocked in specified country."""
    content_details = video_detail.get("contentDetails", {})
    region_restriction = content_details.get("regionRestriction", {})

    blocked = region_restriction.get("blocked", [])
    allowed = region_restriction.get("allowed", [])

    if allowed:
        return country not in allowed
    if blocked:
        return country in blocked

    return False


def classify_video(
    artist: str, video: Dict[str, Any], is_vevo: bool
) -> Tuple[str, str]:
    """
    Classify a video as accept/review/reject.

    Args:
        artist: Artist name
        video: Video metadata
        is_vevo: Whether channel is VEVO

    Returns:
        Tuple of (decision, reason)
    """
    title = video.get("title", "")
    title_l = title.lower()
    description = video.get("description", "").lower()
    duration = video.get("duration", 0)
    published_year = video.get("published_year", 0)
    channel_title = video.get("channel_title", "").lower()

    # Artist-specific ignore
    ignore_keyword = filters.matches_artist_ignore_keywords(artist, title)
    if ignore_keyword:
        return "reject", f"artist_ignore:{ignore_keyword}"

    # Year cutoff
    max_year = filters.get_artist_year_cutoff(artist)
    if max_year and published_year > max_year:
        return "reject", f"year_cutoff:>{max_year}"

    # Duration check
    if not filters.is_valid_duration(duration):
        if duration < config.MIN_DURATION_SEC:
            return "reject", "too_short"
        return "reject", "too_long"

    # Audio-only detection
    if "provided to youtube" in description:
        return "reject", "audio_only"

    # Must look like music video
    is_mv = any(
        phrase in title_l
        for phrase in ["official music video", "official video", "music video"]
    )
    if not is_mv:
        return "reject", "not_music_video"

    # Hard title rejects
    for keyword in config.NEGATIVE_TITLE_HARD:
        if keyword in title_l:
            return "reject", f"hard_negative:{keyword}"

    # Channel blocks
    blocked_keyword = filters.has_blocked_channel_keyword(channel_title)
    if blocked_keyword:
        return "reject", f"bad_channel:{blocked_keyword}"

    # VEVO auto-accept
    if is_vevo:
        return "accept", "vevo_music_video"

    # Score-based classification for non-VEVO
    score = 0

    # Positive signals
    for keyword in config.POSITIVE_TITLE_STRONG:
        if keyword in title_l:
            score += 4

    for keyword in config.POSITIVE_TITLE_WEAK:
        if keyword in title_l:
            score += 2

    # Soft penalties
    for keyword in config.NEGATIVE_TITLE_SOFT:
        if keyword in title_l:
            score -= 2

    # Decide based on score
    if score >= 4:
        return "accept", f"score={score}"
    if score >= 2:
        return "review", f"score={score}"
    return "reject", f"score={score}"


# ============================================================
# Channel Resolution
# ============================================================


def get_channel_metadata(api: YouTubeAPI, channel_id: str) -> Optional[ChannelInfo]:
    channel = api.get_channel_by_id(channel_id)
    if not channel:
        return None

    snippet = channel.get("snippet", {})
    branding = channel.get("brandingSettings", {}).get("channel", {})

    title = snippet.get("title", "")

    return ChannelInfo(
        channel_id=channel_id,
        channel_title=title,
        channel_url=f"https://www.youtube.com/channel/{channel_id}",
        is_vevo="vevo" in title.lower(),
        is_topic=title.lower().endswith(" - topic"),
        is_official_artist=branding.get("isOfficialArtistChannel", False),
    )


def is_viable_channel(api: YouTubeAPI, channel_id: str) -> bool:
    """Check if channel has enough uploads to be viable."""

    metadata = get_channel_metadata(api, channel_id)

    # HARD BLOCK topic channels here
    if not metadata or metadata.is_topic:
        return False

    try:
        videos = api.list_uploads(channel_id)
        return len(videos) >= config.MIN_UPLOADS_FOR_VIABLE_CHANNEL
    except Exception as e:
        logger.warning(f"Uploads check failed for {metadata.channel_title}: {e}")
        return False


def resolve_artist_channel(
    api: YouTubeAPI, artist: str
) -> Tuple[Optional[ChannelInfo], str]:
    """
    Resolve official channel for artist.

    Returns:
        Tuple of (channel_info, matched_via)
    """
    # Try VEVO search
    for query_template in config.VEVO_SEARCH_QUERIES:
        query = query_template.format(artist=artist)
        channel_ids = api.search_channels(query, max_results=3)

        for channel_id in channel_ids:
            metadata = get_channel_metadata(api, channel_id)
            if not metadata or not metadata.is_vevo:
                continue

            if is_viable_channel(api, channel_id):
                return metadata, "vevo_search"

    # Try official channel search
    for query_template in config.OFFICIAL_SEARCH_QUERIES:
        query = query_template.format(artist=artist)
        channel_ids = api.search_channels(query, max_results=5)

        candidates = []
        for channel_id in channel_ids:
            metadata = get_channel_metadata(api, channel_id)
            if not metadata or metadata.is_topic:
                continue
            if is_viable_channel(api, channel_id):
                candidates.append(metadata)

        # Prefer Official Artist Channels first
        for c in candidates:
            if c.is_official_artist:
                return c, "official_artist"

        # Then VEVO
        for c in candidates:
            if c.is_vevo:
                return c, "vevo"

        # Fallback to best viable
        if candidates:
            return candidates[0], "official_search"

    return None, "none"


# ============================================================
# State Management
# ============================================================


def load_state(state_path: Path) -> ArtistState:
    """Load artist discovery state."""
    data = read_json_safe(state_path, default={})
    return ArtistState(
        channel=data.get("channel"),
        processed=data.get("processed", {}),
        completed=data.get("completed", False),
        last_run=data.get("last_run"),
        last_completed=data.get("last_completed"),
    )


def save_state(state_path: Path, state: ArtistState) -> None:
    """Save artist discovery state."""
    data = {
        "channel": state.channel,
        "processed": state.processed,
        "completed": state.completed,
        "last_run": now_utc(),
        "last_completed": state.last_completed,
    }
    write_json(state_path, data)


# ============================================================
# Main Discovery
# ============================================================


def discover_artist(
    api: YouTubeAPI, artist: str, output_dir: Path, force_update: bool = False
) -> DiscoveryStats:
    """
    Discover videos for a single artist.

    Args:
        api: YouTube API wrapper
        artist: Artist name
        output_dir: Output directory
        force_update: Force re-processing

    Returns:
        Discovery statistics
    """
    stats = DiscoveryStats(artist=artist)

    # Load state
    state_path = output_dir / "state.json"
    state = load_state(state_path)

    # Skip if completed
    if state.completed and not force_update:
        logger.debug(f"Skipping {artist} (already completed)")
        return stats

    # Resolve channel
    logger.debug(f"Resolving channel for {artist}...")
    emit_ui_event("task", task="Finding channel")
    channel_info, matched_via = resolve_artist_channel(api, artist)

    if not channel_info:
        logger.warning(f"Could not resolve channel for {artist}")
        stats.matched_via = matched_via

        # Save empty state
        state.completed = True
        save_state(state_path, state)

        write_json(
            output_dir / "summary.json",
            {
                "artist": artist,
                "channel": None,
                "matched_via": matched_via,
                "accepted": 0,
                "review": 0,
                "failed": 0,
            },
        )
        return stats

    logger.debug(f"Found channel: {channel_info.channel_title} ({matched_via})")
    stats.channel = channel_info
    stats.matched_via = matched_via

    emit_ui_event("task", task="Fetching uploads")

    # Get uploads
    uploads = api.list_uploads(channel_info.channel_id)

    fallback_used = False
    fallback_query = None

    if not uploads:
        logger.warning(f"Uploads blocked for {artist}, using search fallback")

        search_results = []

        for q in config.VEVO_SEARCH_QUERIES:
            search_results += api.search_channel_videos(
                q.format(artist=artist), channel_info.channel_id
            )

        for q in config.OFFICIAL_SEARCH_QUERIES:
            search_results += api.search_channel_videos(
                q.format(artist=artist), channel_info.channel_id
            )

        uploads = search_results
        fallback_used = True

    # Get video details
    video_ids = [v["video_id"] for v in uploads]
    details_map = api.get_video_details(video_ids)

    emit_ui_event("task", task="Filtering videos")

    # Process videos
    accepted = []
    review = []
    failed = []

    for video_data in uploads:
        video_id = video_data["video_id"]

        # Skip if already processed
        if not force_update and video_id in state.processed:
            continue

        # Get details
        details = details_map.get(video_id)
        if not details:
            continue

        # Extract metadata
        published_at = video_data.get("published_at", "")
        published_year = int(published_at[:4]) if published_at[:4].isdigit() else 0

        content_details = details.get("contentDetails", {})
        duration = parse_duration_seconds(content_details.get("duration", "PT0S"))
        definition = content_details.get("definition", "sd")

        playable = is_video_playable(details)
        blocked = is_video_blocked(details, config.COUNTRY_CODE)

        # Create entry
        entry = VideoEntry(
            source="fallback" if fallback_used else "original",
            fallback_query=fallback_query if fallback_used else None,
            video_id=video_id,
            title=video_data.get("title", ""),
            description=video_data.get("description", ""),
            published_at=published_at,
            published_year=published_year,
            channel_title=video_data.get("channel_title", ""),
            duration=duration,
            definition=definition,
            url=f"https://www.youtube.com/watch?v={video_id}",
            geo_blocked_here=blocked,
            playable=playable,
        )

        # Classify
        decision, reason = classify_video(artist, entry.__dict__, channel_info.is_vevo)
        entry.reason = reason

        # Categorize
        if decision == "accept":
            accepted.append(entry.__dict__)
            stats.accepted += 1
        elif decision == "review":
            review.append(entry.__dict__)
            stats.review += 1
        else:
            failed.append(entry.__dict__)
            stats.failed += 1

        # Mark as processed
        state.processed[video_id] = {"last_updated": now_utc(), "source": "original"}

    # Save results
    write_json(output_dir / "accepted.json", accepted)
    write_json(output_dir / "review.json", review)
    write_json(output_dir / "failed.json", failed)

    write_json(
        output_dir / "summary.json",
        {
            "artist": artist,
            "channel": channel_info.__dict__,
            "matched_via": matched_via,
            "accepted": stats.accepted,
            "review": stats.review,
            "failed": stats.failed,
        },
    )

    # Update state
    state.completed = True
    state.last_completed = now_utc()
    save_state(state_path, state)

    logger.debug(
        f"{artist}: accepted={stats.accepted}, "
        f"review={stats.review}, failed={stats.failed}"
    )

    return stats


def main() -> int:
    env = get_env()

    # Read inputs from environment
    csv_path = Path(env.artists_csv)
    force_update = env.force_update

    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return 1

    artists = read_artists_csv(csv_path)
    if not artists:
        logger.error("No artists found in CSV")
        return 1

    # Setup API
    api_key_manager = APIKeyManager(env.youtube_api_keys)
    api = YouTubeAPI(api_key_manager)

    csv_stem = csv_path.stem

    try:
        emit_ui_event(
            "stage_start",
            stage="Discovery",
            index=0,
            total=len(artists),
            task="Starting",
        )
        for idx, artist in enumerate(artists, start=1):
            logger.debug(f"Processing: {artist}")

            emit_ui_event(
                "artist_start",
                stage="Discovery",
                index=idx,
                total=len(artists),
                artist=artist,
                task="Finding channel",
                old=0,
                new=0,
                api_key_index=api_key_manager.current_index + 1,
                api_key_total=len(api_key_manager.keys),
            )

            output_dir = discovery_output_path(csv_stem, artist)

            try:
                stats = discover_artist(api, artist, output_dir, force_update)

                emit_ui_event(
                    "artist_done",
                    stage="Discovery",
                    index=idx,
                    total=len(artists),
                    artist=artist,
                    old=stats.review,
                    new=stats.accepted,
                )
            except QuotaExhaustedError:
                logger.warning("YouTube API quota exhausted - stopping discovery")
                emit_ui_event(
                    "detail",
                    line="YouTube API quota exhausted - stopping discovery",
                    style="yellow",
                )
                return 2

            except Exception as e:
                logger.exception(f"Error processing {artist}")
                emit_ui_event("detail", line=f"Error processing {artist}", style="red")
                continue

        logger.debug("Discovery complete!")
        return 0

    except KeyboardInterrupt:
        logger.debug("Discovery interrupted by user")
        return 130


if __name__ == "__main__":
    try:
        sys.exit(main())
    except QuotaExhaustedError:
        logger.warning("YouTube API quota exhausted - stopping")
        sys.exit(2)
