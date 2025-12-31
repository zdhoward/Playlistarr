#!/usr/bin/env python3
"""
playlist_invalidate.py

Builds a plan to remove videos from a playlist that are no longer valid
under current discovery + filter rules.

This script:
- DOES NOT discover new videos
- DOES NOT talk to YouTube
- DOES NOT mutate playlists
- ONLY produces a removal plan

Source of truth:
- out/{csv_stem}/{artist}/accepted.json
- out/{csv_stem}/{artist}/review.json (optional)
- playlist cache for the given playlist_id
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

import config
import filters
from utils import canonicalize_artist, invalidation_plan_path, playlist_cache_path

from logger import get_logger

logger = get_logger(__name__)


def load_artist_csv(path: Path) -> List[str]:
    artists: List[str] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            name = line.strip()
            if name and name.lower() != "artist":
                artists.append(name)
    return artists


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def iter_discovery_entries(artist_dir: Path) -> Iterable[Dict[str, Any]]:
    for fname in ("accepted.json", "review.json"):
        fpath = artist_dir / fname
        data = load_json(fpath)
        if not data:
            continue

        if isinstance(data, list):
            yield from data
        elif isinstance(data, dict):
            yield from data.values()


def build_expected_videos(
    artists: List[str],
    discovery_root: Path,
    logger,
) -> Dict[str, Dict[str, Any]]:
    expected: Dict[str, Dict[str, Any]] = {}

    for artist in artists:
        artist_key = canonicalize_artist(artist)
        artist_dir = discovery_root / artist_key
        if not artist_dir.is_dir():
            logger.debug("[invalidate] No directory for artist: %s", artist)
            continue

        for entry in iter_discovery_entries(artist_dir):
            video_id = entry.get("video_id")
            if not video_id:
                continue

            title = entry.get("title", "")
            channel = entry.get("channel_title", "")

            excluded, _ = filters.is_excluded_version(title)
            if excluded:
                continue

            duration = entry.get("duration")
            if duration is not None and not filters.is_valid_duration(duration):
                continue

            blocked_keyword = filters.has_blocked_channel_keyword(channel)
            if blocked_keyword:
                continue

            if not filters.is_trusted_channel(channel, artist):
                continue

            expected[video_id] = {
                "artist": artist,
                "title": title,
                "channel": channel,
                "url": entry.get("url"),
            }

    return expected


def load_playlist_cache(path: Path) -> Dict[str, Dict[str, Any]]:
    cache = load_json(path)
    if not cache:
        return {}

    items = cache.get("items_by_video_id")
    if not isinstance(items, dict):
        return {}

    return items


def build_invalidation_plan(
    csv_stem: str,
    expected_videos: Dict[str, Dict[str, Any]],
    playlist_videos: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    actions: List[Dict[str, Any]] = []

    expected_ids = set(expected_videos.keys())
    playlist_ids = set(playlist_videos.keys())

    for video_id in sorted(playlist_ids - expected_ids):
        item = playlist_videos[video_id]
        actions.append(
            {
                "action": "remove",
                "video_id": video_id,
                "list_stem": csv_stem,
                "playlist_item_id": item.get("playlist_item_id"),
                "title": item.get("title", "Unknown"),
                "reason": "no_longer_valid",
                "status": "pending",
            }
        )

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "actions": actions,
    }


from env import get_env


def main() -> int:
    # env is already bootstrapped by the parent process
    env = get_env()

    csv_path = Path(env.artists_csv)
    csv_stem = csv_path.stem
    playlist_id = env.playlist_id

    artists = load_artist_csv(csv_path)
    logger.debug("[invalidate] Loaded %d artists", len(artists))

    discovery_root = Path(config.DISCOVERY_ROOT) / csv_stem
    expected = build_expected_videos(artists, discovery_root, logger)
    logger.debug("[invalidate] Expected valid videos: %d", len(expected))

    cache_path = playlist_cache_path(playlist_id)
    playlist_videos = load_playlist_cache(cache_path)
    logger.debug("[invalidate] Playlist videos cached: %d", len(playlist_videos))

    plan_path = invalidation_plan_path(playlist_id)

    if not playlist_videos:
        logger.warning(
            "[invalidate] Playlist cache is empty. Run youtube_playlist_sync first to populate the cache."
        )
        empty_plan = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "actions": [],
        }
        plan_path.write_text(
            json.dumps(empty_plan, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.debug("[invalidate] Created empty plan at %s", plan_path)
        return 0

    plan = build_invalidation_plan(csv_stem, expected, playlist_videos)
    logger.debug("[invalidate] Planned removals: %d", len(plan["actions"]))

    plan_path.write_text(
        json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.debug("[invalidate] Plan written to %s", plan_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
