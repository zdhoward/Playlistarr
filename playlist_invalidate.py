#!/usr/bin/env python3
"""
playlist_invalidate.py

Builds a plan to remove videos from a YouTube playlist that are no longer valid
under current discovery + filter rules.

This script:
- DOES NOT discover new videos
- DOES NOT talk to YouTube
- DOES NOT mutate playlists
- ONLY produces a removal plan

Inputs:
- artists_csv   (same CSV used for discovery)
- playlist_id   (used to locate playlist-specific cache + plan)

Source of truth:
- out/{csv_stem}/{artist}/accepted.json
- out/{csv_stem}/{artist}/review.json (optional)
- playlist cache for the given playlist_id
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

import config
import filters
from utils import playlist_cache_path, invalidation_plan_path

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================
# Helpers
# ============================================================


def load_artist_csv(path: str) -> List[str]:
    """Load artist names from CSV file."""
    artists: List[str] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            name = line.strip()
            if name and name.lower() != "artist":
                artists.append(name)
    return artists


def load_json(path: str) -> Any:
    """Load JSON file, return None if doesn't exist."""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def iter_discovery_entries(artist_dir: str) -> Iterable[Dict[str, Any]]:
    """
    Yield discovery entries from accepted.json and review.json
    for a single artist directory.
    """
    for fname in ("accepted.json", "review.json"):
        fpath = os.path.join(artist_dir, fname)
        data = load_json(fpath)
        if not data:
            continue

        if isinstance(data, list):
            yield from data
        elif isinstance(data, dict):
            yield from data.values()


# ============================================================
# Phase 1 — Build expected video universe
# ============================================================


def build_expected_videos(
    artists: List[str],
    discovery_root: str,
) -> Dict[str, Dict[str, Any]]:
    """
    Returns:
        video_id -> metadata for videos still valid under filters
    """
    expected: Dict[str, Dict[str, Any]] = {}

    for artist in artists:
        artist_dir = os.path.join(discovery_root, artist)
        if not os.path.isdir(artist_dir):
            logger.debug(f"No directory for artist: {artist}")
            continue

        for entry in iter_discovery_entries(artist_dir):
            video_id = entry.get("video_id")
            if not video_id:
                continue

            title = entry.get("title", "")
            channel = entry.get("channel_title", "")

            # 1. Version / title filtering
            excluded, _ = filters.is_excluded_version(title)
            if excluded:
                continue

            # 2. Duration filtering
            duration = entry.get("duration")
            if duration is not None:
                if not filters.is_valid_duration(duration):
                    continue

            # 3. Channel hard block
            blocked_keyword = filters.has_blocked_channel_keyword(channel)
            if blocked_keyword:
                continue

            # 4. Channel trust check
            if not filters.is_trusted_channel(channel, artist):
                continue

            expected[video_id] = {
                "artist": artist,
                "title": title,
                "channel": channel,
                "url": entry.get("url"),
            }

    return expected


# ============================================================
# Phase 2 — Load playlist cache
# ============================================================


def load_playlist_cache(path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Returns:
        video_id -> playlist cache entry
    """
    cache = load_json(str(path))
    if not cache:
        return {}

    items = cache.get("items_by_video_id")
    if not isinstance(items, dict):
        return {}

    return items


# ============================================================
# Phase 3 — Build invalidation plan
# ============================================================


def build_invalidation_plan(
    expected_videos: Dict[str, Dict[str, Any]],
    playlist_videos: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Build plan to remove videos no longer in expected set."""
    actions: List[Dict[str, Any]] = []

    expected_ids = set(expected_videos.keys())
    playlist_ids = set(playlist_videos.keys())

    for video_id in sorted(playlist_ids - expected_ids):
        item = playlist_videos[video_id]

        actions.append(
            {
                "action": "remove",
                "video_id": video_id,
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


# ============================================================
# Entry point
# ============================================================


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate invalidation plan for playlist cleanup"
    )
    parser.add_argument("artists_csv", help="Artist CSV used for discovery")
    parser.add_argument("playlist_id", help="Target YouTube playlist ID")
    args = parser.parse_args()

    csv_path = Path(args.artists_csv)
    csv_stem = csv_path.stem

    artists = load_artist_csv(str(csv_path))
    logger.info(f"[invalidate] Loaded {len(artists)} artists")

    discovery_root = os.path.join(config.DISCOVERY_ROOT, csv_stem)
    expected = build_expected_videos(artists, discovery_root)
    logger.info(f"[invalidate] Expected valid videos: {len(expected)}")

    cache_path = playlist_cache_path(args.playlist_id)
    playlist_videos = load_playlist_cache(cache_path)
    logger.info(f"[invalidate] Playlist videos cached: {len(playlist_videos)}")

    if not playlist_videos:
        logger.warning(
            "[invalidate] Playlist cache is empty. "
            "Run playlist sync first to populate the cache."
        )
        # Create empty plan instead of raising error
        plan = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "actions": [],
        }
        plan_path = invalidation_plan_path(args.playlist_id)
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)
        logger.info(f"[invalidate] Created empty plan at {plan_path}")
        return

    plan = build_invalidation_plan(expected, playlist_videos)
    logger.info(f"[invalidate] Planned removals: {len(plan['actions'])}")

    plan_path = invalidation_plan_path(args.playlist_id)
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    logger.info(f"[invalidate] Plan written to {plan_path}")


if __name__ == "__main__":
    main()
