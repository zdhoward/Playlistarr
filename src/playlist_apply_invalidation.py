#!/usr/bin/env python3
"""
playlist_apply_invalidation.py

Applies a previously generated playlist invalidation plan by removing playlist items.

This script:
- ONLY deletes playlist items
- DOES NOT re-evaluate filters
- IS quota-safe and resumable
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from googleapiclient.errors import HttpError

from api_manager import QuotaExhaustedError, oauth_tripwire
from env import get_env
from logger import get_logger, init_logging
from client import get_youtube_client
from utils import invalidation_plan_path, playlist_cache_path


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def is_quota_exhausted(error: HttpError) -> bool:
    if error.resp.status != 403:
        return False

    try:
        data = json.loads(error.content.decode("utf-8"))
        reasons = [err.get("reason") for err in data.get("error", {}).get("errors", [])]
        return "quotaExceeded" in reasons or "dailyLimitExceeded" in reasons
    except Exception:
        return False


def apply_invalidation(
    yt,
    plan: Dict[str, Any],
    playlist_cache: Dict[str, Any],
    plan_path: Path,
    cache_path: Path,
    logger,
) -> int:
    """
    Returns:
        0  = ok
        10 = quota_exhausted (stopped cleanly)
        20 = failed (errors occurred but continued)
    """
    actions: List[Dict[str, Any]] = plan.get("actions", [])
    items_by_video_id = playlist_cache.get("items_by_video_id", {})

    deleted = 0
    errors = 0
    quota_hit = False

    for action in actions:
        if action.get("status") != "pending":
            continue

        oauth_tripwire()

        playlist_item_id = action.get("playlist_item_id")
        video_id = action.get("video_id")

        if not playlist_item_id:
            action["status"] = "error"
            action["error"] = "missing_playlist_item_id"
            errors += 1
            save_json(plan_path, plan)
            continue

        try:
            yt.playlistItems().delete(id=playlist_item_id).execute()
            time.sleep(1.0)

        except HttpError as e:
            if is_quota_exhausted(e):
                quota_hit = True
                logger.warning("[apply] Quota exhausted - stopping cleanly")
                save_json(plan_path, plan)
                save_json(cache_path, playlist_cache)
                break

            action["status"] = "error"
            action["error"] = f"http_error:{e.resp.status}"
            errors += 1
            logger.warning("[apply] Failed to delete %s: %s", video_id, e)
            save_json(plan_path, plan)
            continue

        except Exception as e:
            action["status"] = "error"
            action["error"] = str(e)
            errors += 1
            logger.warning("[apply] Failed to delete %s: %s", video_id, e)
            save_json(plan_path, plan)
            continue

        action["status"] = "done"
        action["deleted_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        deleted += 1

        if video_id in items_by_video_id:
            del items_by_video_id[video_id]

        save_json(plan_path, plan)
        save_json(cache_path, playlist_cache)

        logger.debug("[apply] Removed %s", video_id)

    logger.debug("[apply] Completed - deleted=%d, errors=%d", deleted, errors)

    if quota_hit:
        return 10
    if errors:
        return 20
    return 0


def _retire_artist_caches(plan: Dict[str, Any], logger) -> None:
    """
    Retire per-artist discovery caches only after all removals for that artist are done.
    """
    actions = plan.get("actions", [])
    if not actions:
        return

    csv_stem = actions[0].get("list_stem")
    if not csv_stem:
        logger.warning("[apply] No list_stem in actions - skipping artist retirement")
        return

    by_artist: dict[str, list[dict[str, Any]]] = {}
    for a in actions:
        artist = a.get("artist")
        if not artist:
            continue
        by_artist.setdefault(artist, []).append(a)

    for artist, items in by_artist.items():
        if not all(a.get("status") == "done" for a in items):
            continue

        artist_dir = Path("../out") / csv_stem / artist
        if artist_dir.exists():
            logger.debug("[apply] Retiring artist cache: %s", artist)
            shutil.rmtree(artist_dir, ignore_errors=True)


def main() -> int:
    init_logging()
    logger = get_logger(__name__)

    env = get_env()
    playlist_id = env.playlist_id

    plan_path = invalidation_plan_path(playlist_id)
    cache_path = playlist_cache_path(playlist_id)

    if not plan_path.exists():
        logger.error("[apply] Missing invalidation plan: %s", plan_path)
        logger.debug("[apply] Run playlist_invalidate first")
        return 20

    if not cache_path.exists():
        logger.error("[apply] Missing playlist cache: %s", cache_path)
        logger.debug("[apply] Run youtube_playlist_sync first to populate the cache")
        return 20

    plan = load_json(plan_path)
    playlist_cache = load_json(cache_path)

    pending = sum(1 for a in plan.get("actions", []) if a.get("status") == "pending")
    logger.debug("[apply] Pending removals: %d", pending)

    if pending == 0:
        logger.debug("[apply] Nothing to do")
        return 0

    youtube = get_youtube_client()
    rc = apply_invalidation(
        youtube,
        plan,
        playlist_cache,
        plan_path,
        cache_path,
        logger,
    )

    _retire_artist_caches(plan, logger)

    return rc


if __name__ == "__main__":
    try:
        sys.exit(main())
    except QuotaExhaustedError:
        # Keep consistent with pipeline semantics
        init_logging()
        logger = get_logger(__name__)
        logger.warning("[apply] YouTube API quota exhausted - stopping")
        sys.exit(10)
