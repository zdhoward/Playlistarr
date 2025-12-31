#!/usr/bin/env python3
"""
youtube_playlist_sync.py (Refactored)

SECOND SCRIPT ONLY:
- OAuth 2.0 authenticate (installed app flow)
- Read accepted.json files produced by your FIRST script
- Add videos into a target playlist safely, idempotently, incrementally
- Cache playlist state locally to reduce quota usage
- Filter version variants (covers, live, remixes) before syncing

It does NOT:
- discover/search videos
- rescore/reclassify
- touch accepted.json
- call MusicBrainz

Key improvements vs original:
- Centralized retry logic via execute_with_retry()
- Typed exception hierarchy for control flow
- More defensive cache validation + cache versioning
- Progress tracking + periodic progress logs
- Health checks (duplicate candidates, cache integrity)

IMPORTANT: Song Key Behavior
This script requires stable song identifiers (song_key, recording_mbid, etc.)
from your first script to enable quality-based replacements. Without these,
each video is treated as unique and replacements won't occur.
"""

from __future__ import annotations

from env import get_env

import argparse
import csv
import json
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    TypeAlias,
    TypeVar,
)

import filters
from client import get_youtube_client
from googleapiclient.errors import HttpError
from utils import playlist_cache_path, canonicalize_artist
from logger import get_logger
from api_manager import (
    QuotaExhaustedError,
    execute_with_retry,
    oauth_exhausted,
    oauth_tripwire,
    mark_oauth_exhausted,
)
from env import PROJECT_ROOT

from logger import get_logger

logger = get_logger(__name__)


# ----------------------------
# Constants / config
# ----------------------------

PLAYLIST_MUTATION_SLEEP = 1.0
YOUTUBE_BATCH_SIZE = 50
CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours
CACHE_VERSION = 1

# Type aliases
YouTubeClient: TypeAlias = Any
T = TypeVar("T")

# ----------------------------
# Exceptions
# ----------------------------


class PlaylistSyncError(Exception):
    """Base exception for playlist sync operations."""


class InvalidPlaylistError(PlaylistSyncError):
    """Raised when playlist is invalid or inaccessible."""


# ----------------------------
# Enums for type safety
# ----------------------------


class VideoDefinition(str, Enum):
    HD = "hd"
    SD = "sd"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> VideoDefinition:
        if not isinstance(value, str):
            return cls.UNKNOWN
        normalized = value.strip().lower()
        try:
            return cls(normalized)
        except ValueError:
            return cls.UNKNOWN

    @property
    def rank(self) -> int:
        return {
            VideoDefinition.HD: 2,
            VideoDefinition.SD: 1,
            VideoDefinition.UNKNOWN: 0,
        }[self]


class VideoSource(str, Enum):
    ORIGINAL = "original"
    FALLBACK = "fallback"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> VideoSource:
        if not isinstance(value, str):
            return cls.UNKNOWN
        normalized = value.strip().lower()
        try:
            return cls(normalized)
        except ValueError:
            return cls.UNKNOWN

    @property
    def rank(self) -> int:
        return {
            VideoSource.ORIGINAL: 2,
            VideoSource.FALLBACK: 1,
            VideoSource.UNKNOWN: 0,
        }[self]


# ----------------------------
# Data model / quality ranking
# ----------------------------


@dataclass(frozen=True)
class Candidate:
    artist: str
    video_id: str
    song_key: str  # stable, non-title key when possible; else falls back to video_id
    title: str
    definition: VideoDefinition
    source: VideoSource

    @property
    def quality_tuple(self) -> Tuple[int, int]:
        """Higher is better: (definition_rank, source_rank)."""
        return (self.definition.rank, self.source.rank)

    @property
    def is_song_key_fallback(self) -> bool:
        """True if song_key is just the video_id (no stable identifier)."""
        return self.song_key == self.video_id

    @staticmethod
    def quality_from_strings(definition: str, source: str) -> Tuple[int, int]:
        def_enum = VideoDefinition.from_string(definition)
        src_enum = VideoSource.from_string(source)
        return (def_enum.rank, src_enum.rank)


@dataclass
class LoadStats:
    """Statistics from loading candidates."""

    total_items: int = 0
    filtered_versions: int = 0
    fallback_count: int = 0
    candidates: List[Candidate] = None  # set in __post_init__

    def __post_init__(self):
        if self.candidates is None:
            self.candidates = []


@dataclass
class Plan:
    already_present: int = 0
    to_add: List[Candidate] = None
    to_replace: List[Tuple[Candidate, str, str]] = (
        None  # (candidate, prev_vid, prev_playlist_item_id)
    )
    skipped_worse: int = 0

    def __post_init__(self) -> None:
        if self.to_add is None:
            self.to_add = []
        if self.to_replace is None:
            self.to_replace = []


@dataclass
class SyncProgress:
    """Track sync progress for periodic reporting."""

    total: int
    processed: int = 0
    added: int = 0
    replaced: int = 0
    removed: int = 0
    failed: int = 0
    skipped_due_to_limit: int = 0

    def maybe_log(self, every: int = 10) -> None:
        if every <= 0:
            return
        if self.processed == 0:
            return
        if self.processed % every != 0 and self.processed != self.total:
            return

        pct = (self.processed / self.total) * 100.0 if self.total else 100.0
        logger.debug(
            f"Progress: {self.processed}/{self.total} ({pct:.1f}%) | "
            f"added={self.added} replaced={self.replaced} removed={self.removed} "
            f"failed={self.failed} skipped_limit={self.skipped_due_to_limit}"
        )


# ----------------------------
# Basic helpers
# ----------------------------


def _now() -> int:
    return int(time.time())


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, sort_keys=True)
    tmp.replace(path)


def _http_reason(e: HttpError) -> str:
    try:
        data = e.error_details if hasattr(e, "error_details") else None
        if data:
            return str(data)
    except Exception:
        pass
    try:
        body = (
            e.content.decode("utf-8", errors="replace") if hasattr(e, "content") else ""
        )
        return body[:300]
    except Exception:
        return str(e)


# ----------------------------
# OAuth / YouTube client
# ----------------------------


def validate_playlist_access(youtube: YouTubeClient, playlist_id: str) -> None:
    """Verify playlist exists and is accessible; raise InvalidPlaylistError if not."""
    try:
        time.sleep(PLAYLIST_MUTATION_SLEEP)

        def _op() -> Any:
            oauth_tripwire()
            return (
                youtube.playlists()
                .list(
                    part="snippet",
                    id=playlist_id,
                    maxResults=1,
                )
                .execute()
            )

        execute_with_retry(_op, operation_name="validate playlist access")
    except QuotaExhaustedError:
        # If quota is exhausted even during validation, bubble up as-is.
        mark_oauth_exhausted()
        raise
    except HttpError as e:
        raise InvalidPlaylistError(
            f"Cannot access playlist {playlist_id}: {_http_reason(e)}"
        ) from e


# ----------------------------
# accepted.json ingestion
# ----------------------------


def _extract_video_id(item: Dict[str, Any]) -> Optional[str]:
    for k in ("videoId", "video_id", "videoID", "id"):
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()

    rid = item.get("resourceId")
    if isinstance(rid, dict):
        v = rid.get("videoId")
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _extract_title(item: Dict[str, Any]) -> str:
    title = item.get("title") or item.get("snippet", {}).get("title", "")
    return str(title) if title else ""


def _extract_source(item: Dict[str, Any]) -> VideoSource:
    v = item.get("source")
    return VideoSource.from_string(v) if v else VideoSource.UNKNOWN


def _extract_definition(item: Dict[str, Any]) -> VideoDefinition:
    v = item.get("definition")
    return VideoDefinition.from_string(v) if v else VideoDefinition.UNKNOWN


def _extract_song_key(item: Dict[str, Any], video_id: str) -> str:
    """
    Extract stable song identifier. No title-based matching.

    Prefer explicit stable identifiers if present; else fall back to video_id.
    """
    for k in (
        "song_key",
        "track_key",
        "recording_mbid",
        "work_mbid",
        "release_mbid",
        "track_id",
        "musicbrainz_recording_id",
        "musicbrainz_work_id",
    ):
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()

    song = item.get("song")
    if isinstance(song, dict):
        for k in ("key", "id", "recording_mbid", "work_mbid"):
            v = song.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()

    return video_id


def load_candidates_from_out_root(
    out_root: Path,
    enable_filtering: bool = True,
    allowed_keys: set[str] | None = None,
) -> LoadStats:
    """
    Scans: out/<stem>/**/accepted.json
    Returns: LoadStats with best candidate per song_key + filtering statistics
    """
    accepted_paths = sorted(out_root.rglob("accepted.json"))
    candidates_by_song: Dict[str, Candidate] = {}
    stats = LoadStats()

    for p in accepted_paths:
        artist = p.parent.name

        if allowed_keys is not None and artist not in allowed_keys:
            logger.debug(f"Skipping orphaned artist folder: {artist}")
            continue

        try:
            data = _read_json(p)
        except Exception as e:
            logger.warning(f"Failed to read {p}: {e}")
            continue

        for item in data:
            if not isinstance(item, dict):
                continue

            stats.total_items += 1

            vid = _extract_video_id(item)
            if not vid:
                continue

            title = _extract_title(item)

            if enable_filtering:
                is_excluded, pattern = filters.is_excluded_version(title)
                if is_excluded:
                    stats.filtered_versions += 1
                    logger.debug(
                        f"Filtered version variant: {title[:80]} (pattern: {pattern})"
                    )
                    continue

            source = _extract_source(item)
            definition = _extract_definition(item)
            song_key = _extract_song_key(item, vid)

            cand = Candidate(
                artist=artist,
                video_id=vid,
                song_key=song_key,
                title=title,
                definition=definition,
                source=source,
            )

            if cand.is_song_key_fallback:
                stats.fallback_count += 1

            prev = candidates_by_song.get(song_key)
            if prev is None or cand.quality_tuple > prev.quality_tuple:
                candidates_by_song[song_key] = cand

    stats.candidates = list(candidates_by_song.values())
    return stats


# ----------------------------
# Playlist cache + fetch
# ----------------------------


def read_artists(csv_path: Path) -> set[str]:
    artists: set[str] = set()
    try:
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            first_row = next(reader, None)
            if first_row and first_row[0].lower() != "artist":
                artists.add(first_row[0])

            for row in reader:
                if row and row[0].strip():
                    artists.add(row[0].strip())
    except Exception as e:
        logger.error(f"Failed to read artists from {csv_path}: {e}")
        raise

    return artists


def validate_cache_structure(cache: Dict[str, Any]) -> bool:
    required_keys = {"version", "playlist_id", "fetched_at", "items_by_video_id"}
    if not required_keys.issubset(cache):
        missing = sorted(required_keys - set(cache.keys()))
        logger.warning(f"Cache missing required keys: {missing}")
        return False

    if cache.get("version") != CACHE_VERSION:
        logger.warning(
            f"Cache version mismatch: got {cache.get('version')} expected {CACHE_VERSION}"
        )
        return False

    if not isinstance(cache.get("items_by_video_id"), dict):
        logger.warning("Cache items_by_video_id is not a dict")
        return False

    # song_key_to_video_id is optional but if present must be dict
    sk = cache.get("song_key_to_video_id")
    if sk is not None and not isinstance(sk, dict):
        logger.warning("Cache song_key_to_video_id is not a dict")
        return False

    return True


def load_cache(cache_path: Path) -> Dict[str, Any]:
    if not cache_path.exists():
        return {}

    try:
        obj = _read_json(cache_path)
        if isinstance(obj, dict) and validate_cache_structure(obj):
            return obj
        logger.warning("Cache invalid or unsupported; starting fresh.")
    except Exception as e:
        logger.warning(f"Cache file corrupted, starting fresh: {e}")

    return {}


def cache_is_fresh(cache: Dict[str, Any], playlist_id: str) -> bool:
    if cache.get("playlist_id") != playlist_id:
        return False
    fetched_at = cache.get("fetched_at")
    if not isinstance(fetched_at, int):
        return False
    return (_now() - fetched_at) <= CACHE_TTL_SECONDS


def fetch_playlist_items(
    youtube: YouTubeClient, playlist_id: str
) -> List[Dict[str, Any]]:
    """
    Fetch all playlist items (videoId + playlistItemId).
    Uses playlistItems.list paging.
    """
    items: List[Dict[str, Any]] = []
    page_token: Optional[str] = None

    while True:
        time.sleep(PLAYLIST_MUTATION_SLEEP)

        def _op() -> Any:
            oauth_tripwire()
            return (
                youtube.playlistItems()
                .list(
                    part="contentDetails,snippet",
                    playlistId=playlist_id,
                    maxResults=YOUTUBE_BATCH_SIZE,
                    pageToken=page_token,
                )
                .execute()
            )

        resp = execute_with_retry(_op, operation_name="fetch playlistItems.list")

        for it in resp.get("items", []):
            cd = it.get("contentDetails") or {}
            video_id = cd.get("videoId")
            playlist_item_id = it.get("id")
            if isinstance(video_id, str) and isinstance(playlist_item_id, str):
                items.append(
                    {"video_id": video_id, "playlist_item_id": playlist_item_id}
                )

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return items


def fetch_video_definitions(
    youtube: YouTubeClient, video_ids: Iterable[str]
) -> Dict[str, VideoDefinition]:
    """
    Batch-fetch video definition via videos.list (up to 50 ids per call).
    Returns map: video_id -> VideoDefinition enum
    """
    ids = [v for v in dict.fromkeys(video_ids) if isinstance(v, str) and v]
    out: Dict[str, VideoDefinition] = {}

    for i in range(0, len(ids), YOUTUBE_BATCH_SIZE):
        chunk = ids[i : i + YOUTUBE_BATCH_SIZE]

        time.sleep(PLAYLIST_MUTATION_SLEEP)

        def _op() -> Any:
            oauth_tripwire()
            return (
                youtube.videos()
                .list(
                    part="contentDetails",
                    id=",".join(chunk),
                    maxResults=YOUTUBE_BATCH_SIZE,
                )
                .execute()
            )

        try:
            resp = execute_with_retry(
                _op, operation_name="fetch videos.list definitions"
            )
        except QuotaExhaustedError:
            mark_oauth_exhausted()
            raise
        except HttpError as e:
            logger.warning(
                f"videos.list failed; continuing without definitions. ({_http_reason(e)})"
            )
            return out

        for it in resp.get("items", []):
            vid = it.get("id")
            cd = it.get("contentDetails") or {}
            definition = cd.get("definition")
            if isinstance(vid, str):
                out[vid] = VideoDefinition.from_string(definition)

    return out


def build_playlist_state(
    youtube: YouTubeClient,
    playlist_id: str,
    cache_path: Path,
    force_update: bool,
) -> Dict[str, Any]:
    """
    Returns dict with:
      - version
      - playlist_id
      - fetched_at
      - items_by_video_id: { videoId: {playlist_item_id, song_key?, quality?, artist?, added_by_script?} }
      - song_key_to_video_id: { song_key: videoId } (only for items added/known by this script)
    """
    cache = load_cache(cache_path)

    if not force_update and cache and cache_is_fresh(cache, playlist_id):
        logger.debug("Using cached playlist state")
        return cache

    logger.debug("Fetching fresh playlist state from YouTube...")

    time.sleep(PLAYLIST_MUTATION_SLEEP)
    items = fetch_playlist_items(youtube, playlist_id)

    prev_items_by_video = (
        cache.get("items_by_video_id", {})
        if isinstance(cache.get("items_by_video_id"), dict)
        else {}
    )
    prev_song_map = (
        cache.get("song_key_to_video_id", {})
        if isinstance(cache.get("song_key_to_video_id"), dict)
        else {}
    )

    items_by_video_id: Dict[str, Any] = {}
    for it in items:
        vid = it["video_id"]
        items_by_video_id[vid] = {"playlist_item_id": it["playlist_item_id"]}

        # carry over tracked metadata for known videos
        if vid in prev_items_by_video and isinstance(prev_items_by_video[vid], dict):
            for k in ("song_key", "quality", "added_by_script", "artist"):
                if k in prev_items_by_video[vid]:
                    items_by_video_id[vid][k] = prev_items_by_video[vid][k]

    new_cache = {
        "version": CACHE_VERSION,
        "playlist_id": playlist_id,
        "fetched_at": _now(),
        "items_by_video_id": items_by_video_id,
        "song_key_to_video_id": prev_song_map,
    }

    _write_json(cache_path, new_cache)
    logger.debug(f"Cached {len(items)} playlist items")
    return new_cache


# ----------------------------
# Write operations (safe)
# ----------------------------


def playlist_insert(youtube: YouTubeClient, playlist_id: str, video_id: str) -> str:
    """Insert video into playlist. Returns playlistItemId."""
    time.sleep(PLAYLIST_MUTATION_SLEEP)

    def _op() -> Any:
        oauth_tripwire()
        return (
            youtube.playlistItems()
            .insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": video_id},
                    }
                },
            )
            .execute()
        )

    resp = execute_with_retry(_op, operation_name=f"insert {video_id}")
    return resp.get("id")


def playlist_delete(youtube: YouTubeClient, playlist_item_id: str) -> None:
    """Delete item from playlist by playlistItemId."""
    time.sleep(PLAYLIST_MUTATION_SLEEP)

    def _op() -> Any:
        oauth_tripwire()
        return youtube.playlistItems().delete(id=playlist_item_id).execute()

    execute_with_retry(_op, operation_name=f"delete playlistItemId={playlist_item_id}")


# ----------------------------
# Planning: adds vs replacements
# ----------------------------


def _enrich_candidate_definitions(
    candidates: List[Candidate], youtube: YouTubeClient
) -> List[Candidate]:
    need_defs = [
        c.video_id for c in candidates if c.definition == VideoDefinition.UNKNOWN
    ]
    if not need_defs:
        return candidates

    logger.debug(f"Fetching definitions for {len(need_defs)} videos...")
    defs = fetch_video_definitions(youtube, need_defs)

    enriched: List[Candidate] = []
    for c in candidates:
        if c.definition == VideoDefinition.UNKNOWN and c.video_id in defs:
            enriched.append(
                Candidate(
                    artist=c.artist,
                    video_id=c.video_id,
                    song_key=c.song_key,
                    title=c.title,
                    definition=defs[c.video_id],
                    source=c.source,
                )
            )
        else:
            enriched.append(c)

    return enriched


def _check_for_replacement(
    candidate: Candidate,
    song_map: Dict[str, str],
    items_by_video: Dict[str, Any],
) -> Optional[Tuple[str, str, Tuple[int, int]]]:
    """
    Check if candidate should replace existing video.
    Returns: (prev_video_id, playlist_item_id, prev_quality) or None
    """
    prev_vid = song_map.get(candidate.song_key)
    if not isinstance(prev_vid, str) or prev_vid not in items_by_video:
        return None

    prev_meta = items_by_video.get(prev_vid) or {}
    if not isinstance(prev_meta, dict):
        return None

    prev_quality = (0, 0)
    q = prev_meta.get("quality")
    if isinstance(q, dict):
        prev_def = str(q.get("definition", "unknown")).lower()
        prev_src = str(q.get("source", "unknown")).lower()
        prev_quality = Candidate.quality_from_strings(prev_def, prev_src)

    if candidate.quality_tuple <= prev_quality:
        return None

    playlist_item_id = prev_meta.get("playlist_item_id")
    if not isinstance(playlist_item_id, str) or not playlist_item_id:
        return None

    return (prev_vid, playlist_item_id, prev_quality)


def plan_changes(
    candidates: List[Candidate],
    playlist_state: Dict[str, Any],
    youtube: YouTubeClient,
) -> Plan:
    """
    Plan additions and replacements.

    Rules:
    1) Never add duplicate videoIds already in playlist.
    2) Only replace if strictly better AND we can prove same song via song_key mapping in cache.
       (No title matching. No guessing.)
    """
    plan = Plan()

    items_by_video = playlist_state.get("items_by_video_id") or {}
    if not isinstance(items_by_video, dict):
        items_by_video = {}

    song_map = playlist_state.get("song_key_to_video_id") or {}
    if not isinstance(song_map, dict):
        song_map = {}

    existing_video_ids = set(items_by_video.keys())

    enriched = _enrich_candidate_definitions(candidates, youtube)
    enriched.sort(key=lambda c: (c.artist.lower(), c.song_key, c.video_id))

    for c in enriched:
        if c.video_id in existing_video_ids:
            plan.already_present += 1
            continue

        replacement_info = _check_for_replacement(c, song_map, items_by_video)
        if replacement_info:
            prev_vid, playlist_item_id, _prev_quality = replacement_info
            plan.to_replace.append((c, prev_vid, playlist_item_id))
        elif c.song_key in song_map and song_map[c.song_key] in existing_video_ids:
            plan.skipped_worse += 1
        else:
            plan.to_add.append(c)

    return plan


def plan_removals(
    playlist_state: Dict[str, Any],
    allowed_artists: set[str],
) -> List[Tuple[str, str, str]]:
    """
    Returns list of (video_id, playlist_item_id, artist) to delete.
    Only removes items that were added by this script.
    """
    removals: List[Tuple[str, str, str]] = []

    items = playlist_state.get("items_by_video_id", {})
    if not isinstance(items, dict):
        return removals

    for video_id, meta in items.items():
        if not isinstance(meta, dict):
            continue
        if not meta.get("added_by_script"):
            continue

        artist = meta.get("artist")
        if artist and artist not in allowed_artists:
            pi = meta.get("playlist_item_id")
            if isinstance(pi, str) and pi:
                removals.append((video_id, pi, artist))

    return removals


# ----------------------------
# CLI / main
# ----------------------------


def parse_args(argv: List[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="OAuth + idempotent incremental sync from out/<stem>/**/accepted.json into a YouTube playlist.",
        epilog="See script docstring for examples and important notes about song_key behavior.",
    )
    ap.add_argument("csv_file", help="CSV file used for discovery (e.g., artists.csv)")
    ap.add_argument("playlist_id", help="Target YouTube playlist ID")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be added/replaced; no writes",
    )
    ap.add_argument(
        "--force-update",
        action="store_true",
        help="Re-fetch playlist state even if cache is fresh",
    )
    ap.add_argument(
        "--max-add",
        type=int,
        default=0,
        help="Limit number of inserts performed (0 = no limit)",
    )
    ap.add_argument(
        "--no-filter",
        action="store_true",
        help="Disable version filtering (sync all accepted.json)",
    )
    ap.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    ap.add_argument(
        "--progress-every",
        type=int,
        default=10,
        help="Log progress every N operations (0 disables)",
    )
    return ap.parse_args(argv)


from env import get_env


def main() -> int:
    # env is already bootstrapped by the parent process
    env = get_env()

    csv_path = Path(env.artists_csv)
    stem = csv_path.stem

    # Resolve out_root relative to project root so stage execution cwd cannot break it.
    out_root = (PROJECT_ROOT / "out" / stem).resolve()

    cache_path = playlist_cache_path(env.playlist_id)

    if not out_root.exists():
        logger.error(f"Expected input root folder does not exist: {out_root}")
        return 2

    youtube = get_youtube_client()

    try:
        if oauth_exhausted():
            logger.warning("OAuth quota exhausted - stopping sync")
            return 2

        # Health check: playlist access
        validate_playlist_access(youtube, env.playlist_id)

        # 1) Load candidates
        enable_filtering = not env.no_filter
        logger.debug(
            f"Loading candidates from {out_root}... (filtering={'enabled' if enable_filtering else 'disabled'})"
        )
        allowed_keys = {canonicalize_artist(a) for a in read_artists(csv_path)}
        load_stats = load_candidates_from_out_root(
            out_root, enable_filtering, allowed_keys
        )
        candidates = load_stats.candidates

        if not candidates:
            logger.debug(f"No candidates found under: {out_root}")
            return 0

        # Health check: duplicate video_ids in candidates
        candidate_ids = [c.video_id for c in candidates]
        dup_count = len(candidate_ids) - len(set(candidate_ids))
        if dup_count > 0:
            logger.warning(
                f"Health check: {dup_count} duplicate video_id(s) in candidates (best-per-song_key may hide some)"
            )

        # Report filtering statistics
        if (
            enable_filtering
            and load_stats.filtered_versions > 0
            and load_stats.total_items > 0
        ):
            logger.debug(
                f"Version filtering: excluded {load_stats.filtered_versions}/{load_stats.total_items} items "
                f"({100.0 * load_stats.filtered_versions / load_stats.total_items:.1f}%)"
            )

        if load_stats.fallback_count > 0:
            logger.warning(
                f"{load_stats.fallback_count}/{len(candidates)} candidates using video_id as song_key. "
                f"Quality-based replacements require stable identifiers from your first script."
            )

        # 2) Load playlist state
        playlist_state = build_playlist_state(
            youtube=youtube,
            playlist_id=env.playlist_id,
            cache_path=cache_path,
            force_update=env.force_update,
        )

        # Cache health check: if somehow invalid, force refresh
        if (
            playlist_state
            and isinstance(playlist_state, dict)
            and not validate_cache_structure(playlist_state)
        ):
            logger.warning("Cache health check failed; forcing refresh from YouTube")
            playlist_state = build_playlist_state(
                youtube=youtube,
                playlist_id=env.playlist_id,
                cache_path=cache_path,
                force_update=True,
            )

        # Plan removals
        allowed_keys = {canonicalize_artist(a) for a in read_artists(csv_path)}
        removals = plan_removals(playlist_state, allowed_keys)

        # 3) Plan changes
        logger.debug("Planning changes...")
        plan = plan_changes(candidates, playlist_state, youtube)

        logger.debug("=" * 80)
        logger.debug(f"Out root:          {out_root}")
        logger.debug(f"Playlist ID:       {env.playlist_id}")
        logger.debug(f"Total items found: {load_stats.total_items}")
        logger.debug(
            f"Filtered versions: {load_stats.filtered_versions} ({'disabled' if env.no_filter else 'enabled'})"
        )
        logger.debug(
            f"Candidates:        {len(candidates)} (best-per-song_key after filtering)"
        )
        logger.debug(f"Already present:   {plan.already_present}")
        logger.debug(f"Planned adds:      {len(plan.to_add)}")
        logger.debug(
            f"Planned replaces:  {len(plan.to_replace)} (only when song_key mapping exists + strictly better)"
        )
        logger.debug(f"Skipped (worse):   {plan.skipped_worse}")
        logger.debug(f"Planned removals:  {len(removals)}")
        logger.debug(f"Dry run:           {bool(env.dry_run)}")
        logger.debug(f"Max add limit:     {env.max_add if env.max_add else 'none'}")
        logger.debug("=" * 80)

        if env.dry_run:
            if plan.to_replace:
                logger.debug("\n[DRY-RUN] Replacements:")
                for c, prev_vid, _prev_pi in plan.to_replace[:50]:
                    logger.debug(
                        f"  - song_key={c.song_key}  replace {prev_vid} -> {c.video_id}  quality={c.quality_tuple}  artist={c.artist}"
                    )
                    logger.debug(f"    title: {c.title[:80]}")
                if len(plan.to_replace) > 50:
                    logger.debug(f"  ... ({len(plan.to_replace) - 50} more)")

            if plan.to_add:
                logger.debug("\n[DRY-RUN] Additions:")
                for c in plan.to_add[:50]:
                    logger.debug(
                        f"  - add {c.video_id}  song_key={c.song_key}  quality={c.quality_tuple}  artist={c.artist}"
                    )
                    logger.debug(f"    title: {c.title[:80]}")
                if len(plan.to_add) > 50:
                    logger.debug(f"  ... ({len(plan.to_add) - 50} more)")

            if removals:
                logger.debug("\n[DRY-RUN] Removals:")
                for video_id, _pi, artist in removals[:50]:
                    logger.debug(
                        f"  - remove {video_id}  artist={artist} (no longer in CSV)"
                    )
                if len(removals) > 50:
                    logger.debug(f"  ... ({len(removals) - 50} more)")

            return 0

        # 4) Execute writes
        items_by_video = playlist_state.get("items_by_video_id") or {}
        if not isinstance(items_by_video, dict):
            items_by_video = {}
        song_map = playlist_state.get("song_key_to_video_id") or {}
        if not isinstance(song_map, dict):
            song_map = {}

        added = 0
        replaced = 0
        failed = 0
        skipped_due_to_limit = 0
        removed = 0

        def can_insert_more() -> bool:
            if env.max_add and env.max_add > 0:
                return added < env.max_add
            return True

        def save_state() -> None:
            playlist_state["version"] = CACHE_VERSION
            playlist_state["items_by_video_id"] = items_by_video
            playlist_state["song_key_to_video_id"] = song_map
            playlist_state["fetched_at"] = _now()
            _write_json(cache_path, playlist_state)

        total_ops = len(plan.to_replace) + len(plan.to_add) + len(removals)
        progress = SyncProgress(total=total_ops)

        try:
            # Replacements: insert-then-delete
            if plan.to_replace:
                logger.debug("Executing replacements...")

            for c, prev_vid, prev_pi in plan.to_replace:
                if not can_insert_more():
                    skipped_due_to_limit += 1
                    progress.skipped_due_to_limit += 1
                    progress.processed += 1
                    progress.maybe_log(env.progress_every)
                    continue

                try:
                    new_pi = playlist_insert(youtube, env.playlist_id, c.video_id)
                    added += 1
                    replaced += 1
                    progress.added += 1
                    progress.replaced += 1

                    logger.debug(
                        f"Inserted {c.video_id} (playlistItemId={new_pi}) for song_key={c.song_key}"
                    )

                    items_by_video[c.video_id] = {
                        "artist": c.artist,
                        "playlist_item_id": new_pi,
                        "song_key": c.song_key,
                        "quality": {
                            "definition": c.definition.value,
                            "source": c.source.value,
                        },
                        "added_by_script": True,
                    }
                    song_map[c.song_key] = c.video_id

                    # Best-effort delete old
                    try:
                        playlist_delete(youtube, prev_pi)
                        logger.debug(
                            f"Deleted old {prev_vid} (playlistItemId={prev_pi})"
                        )
                        items_by_video.pop(prev_vid, None)
                    except HttpError as e:
                        failed += 1
                        progress.failed += 1
                        logger.warning(
                            f"Delete failed for old {prev_vid} (playlistItemId={prev_pi}); continuing. ({_http_reason(e)})"
                        )

                except QuotaExhaustedError:
                    mark_oauth_exhausted()
                    logger.warning(
                        "Quota exhausted during replacements. Saving progress..."
                    )
                    save_state()
                    logger.debug(
                        f"\n[STOP] Quota exhausted. Progress: added={added}, replaced={replaced}, failed={failed}"
                    )
                    return 1
                except HttpError as e:
                    failed += 1
                    progress.failed += 1
                    logger.error(
                        f"Replacement insert failed for {c.video_id}; skipping. ({_http_reason(e)})"
                    )
                except Exception as e:
                    failed += 1
                    progress.failed += 1
                    logger.error(
                        f"Replacement failed for {c.video_id}; skipping. ({e})"
                    )

                progress.processed += 1
                progress.maybe_log(env.progress_every)

            # Additions
            if plan.to_add:
                logger.debug("Executing additions...")

            for c in plan.to_add:
                if not can_insert_more():
                    skipped_due_to_limit += 1
                    progress.skipped_due_to_limit += 1
                    progress.processed += 1
                    progress.maybe_log(env.progress_every)
                    continue

                if c.video_id in items_by_video:
                    progress.processed += 1
                    progress.maybe_log(env.progress_every)
                    continue

                try:
                    pi = playlist_insert(youtube, env.playlist_id, c.video_id)
                    added += 1
                    progress.added += 1
                    logger.debug(
                        f"Added {c.video_id} (playlistItemId={pi}) song_key={c.song_key} artist={c.artist}"
                    )

                    items_by_video[c.video_id] = {
                        "artist": c.artist,
                        "playlist_item_id": pi,
                        "song_key": c.song_key,
                        "quality": {
                            "definition": c.definition.value,
                            "source": c.source.value,
                        },
                        "added_by_script": True,
                    }
                    song_map[c.song_key] = c.video_id

                except QuotaExhaustedError:
                    mark_oauth_exhausted()
                    logger.warning(
                        "Quota exhausted during additions. Saving progress..."
                    )
                    save_state()
                    logger.debug(
                        f"\n[STOP] Quota exhausted. Progress: added={added}, replaced={replaced}, failed={failed}"
                    )
                    return 1
                except HttpError as e:
                    failed += 1
                    progress.failed += 1
                    logger.error(
                        f"Insert failed for {c.video_id}; skipping. ({_http_reason(e)})"
                    )
                except Exception as e:
                    failed += 1
                    progress.failed += 1
                    logger.error(f"Insert failed for {c.video_id}; skipping. ({e})")

                progress.processed += 1
                progress.maybe_log(env.progress_every)

            # Removals
            if removals:
                logger.debug("Executing removals...")

            for video_id, playlist_item_id, artist in removals:
                try:
                    playlist_delete(youtube, playlist_item_id)
                    logger.debug(f"Removed {video_id} (artist={artist})")
                    items_by_video.pop(video_id, None)
                    removed += 1
                    progress.removed += 1

                    # remove from song_map if present
                    song_key = None
                    for sk, vid in list(song_map.items()):
                        if vid == video_id:
                            song_key = sk
                            break
                    if song_key:
                        song_map.pop(song_key, None)

                except QuotaExhaustedError:
                    mark_oauth_exhausted()
                    logger.warning(
                        "Quota exhausted during removals. Saving progress..."
                    )
                    save_state()
                    logger.debug(
                        f"\n[STOP] Quota exhausted. Progress: added={added}, replaced={replaced}, failed={failed}"
                    )
                    return 1
                except HttpError as e:
                    failed += 1
                    progress.failed += 1
                    logger.warning(f"Failed to remove {video_id}: {_http_reason(e)}")
                except Exception as e:
                    failed += 1
                    progress.failed += 1
                    logger.warning(f"Failed to remove {video_id}: {e}")

                progress.processed += 1
                progress.maybe_log(env.progress_every)

        finally:
            # Always persist the latest known state at the end of execution phase
            save_state()

        logger.debug("\n" + "=" * 80)
        logger.debug("[DONE]")
        logger.debug(f"Already present:          {plan.already_present}")
        logger.debug(f"Added (inserts):          {added}")
        logger.debug(f"Replaced (subset of add): {replaced}")
        logger.debug(f"Removed:                  {removed}")
        logger.debug(f"Skipped (worse):          {plan.skipped_worse}")
        logger.debug(f"Skipped (max-add limit):  {skipped_due_to_limit}")
        logger.debug(f"Failures (non-fatal):     {failed}")
        logger.debug(f"Cache updated:            {cache_path}")
        logger.debug("=" * 80)
        return 0

    except InvalidPlaylistError as e:
        logger.error(str(e))
        return 1
    except QuotaExhaustedError as e:
        mark_oauth_exhausted()
        logger.warning(str(e))
        return 1
    except Exception as e:
        logger.exception(f"Unhandled error: {e}")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except QuotaExhaustedError:
        mark_oauth_exhausted()
        logger.warning("YouTube API quota exhausted - stopping")
        sys.exit(2)
