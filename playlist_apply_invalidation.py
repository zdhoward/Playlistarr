#!/usr/bin/env python3
"""
playlist_apply_invalidation.py

Applies a previously generated playlist invalidation plan by
removing playlist items from YouTube.

This script:
- ONLY deletes playlist items
- DOES NOT re-evaluate filters
- IS quota-safe and resumable
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List
import shutil

from googleapiclient.errors import HttpError

from client import get_youtube_client
from utils import playlist_cache_path, invalidation_plan_path

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================
# JSON helpers
# ============================================================


def load_json(path: Path) -> Any:
    """Load JSON from file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    """Save JSON to file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ============================================================
# Quota handling
# ============================================================


def is_quota_exhausted(error: HttpError) -> bool:
    """Check if error indicates quota exhaustion."""
    if error.resp.status != 403:
        return False

    try:
        data = json.loads(error.content.decode("utf-8"))
        reasons = [err.get("reason") for err in data.get("error", {}).get("errors", [])]
        return "quotaExceeded" in reasons or "dailyLimitExceeded" in reasons
    except Exception:
        return False


# ============================================================
# Apply invalidation actions
# ============================================================


def apply_invalidation(
    yt,
    plan: Dict[str, Any],
    playlist_cache: Dict[str, Any],
    plan_path: Path,
    cache_path: Path,
) -> None:
    """Execute the invalidation plan."""
    actions: List[Dict[str, Any]] = plan.get("actions", [])
    items_by_video_id = playlist_cache.get("items_by_video_id", {})

    deleted = 0
    errors = 0

    for action in actions:
        if action.get("status") != "pending":
            continue

        playlist_item_id = action.get("playlist_item_id")
        video_id = action.get("video_id")

        if not playlist_item_id:
            action["status"] = "error"
            action["error"] = "missing_playlist_item_id"
            errors += 1
            continue

        try:
            yt.playlistItems().delete(id=playlist_item_id).execute()
            time.sleep(1.0)

        except HttpError as e:
            if is_quota_exhausted(e):
                logger.error("[apply] Quota exhausted — stopping cleanly")
                save_json(plan_path, plan)
                save_json(cache_path, playlist_cache)
                break

            action["status"] = "error"
            action["error"] = f"http_error:{e.resp.status}"
            errors += 1
            logger.warning(f"[apply] Failed to delete {video_id}: {e}")
            continue

        except Exception as e:
            action["status"] = "error"
            action["error"] = str(e)
            errors += 1
            logger.warning(f"[apply] Failed to delete {video_id}: {e}")
            continue

        # Success
        action["status"] = "done"
        action["deleted_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        deleted += 1

        if video_id in items_by_video_id:
            del items_by_video_id[video_id]

        # Persist progress after every successful delete
        save_json(plan_path, plan)
        save_json(cache_path, playlist_cache)

        logger.info(f"[apply] Removed {video_id}")

    logger.info(f"[apply] Completed — deleted={deleted}, errors={errors}")


# ============================================================
# Entry point
# ============================================================


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Apply invalidation plan to remove videos from playlist"
    )
    parser.add_argument("playlist_id", help="Target YouTube playlist ID")
    args = parser.parse_args()

    plan_path = invalidation_plan_path(args.playlist_id)
    cache_path = playlist_cache_path(args.playlist_id)

    if not plan_path.exists():
        logger.error(f"[apply] Missing invalidation plan: {plan_path}")
        logger.info("[apply] Run playlist_invalidate.py first")
        return

    if not cache_path.exists():
        logger.error(f"[apply] Missing playlist cache: {cache_path}")
        logger.info("[apply] Run youtube_playlist_sync.py first")
        return

    plan = load_json(plan_path)
    playlist_cache = load_json(cache_path)

    pending = sum(1 for a in plan.get("actions", []) if a.get("status") == "pending")
    logger.info(f"[apply] Pending removals: {pending}")

    if pending == 0:
        logger.info("[apply] Nothing to do")
        return

    youtube = get_youtube_client()
    apply_invalidation(
        youtube,
        plan,
        playlist_cache,
        plan_path,
        cache_path,
    )

    # ============================================================
    # Retire artist discovery caches once fully removed
    # ============================================================

    actions = plan.get("actions", [])
    if not actions:
        return

    csv_stem = actions[0].get("list_stem")
    if not csv_stem:
        logger.warning("[apply] No list_stem in actions — skipping artist retirement")
        return

    # Group actions by artist
    by_artist = {}
    for a in plan.get("actions", []):
        artist = a.get("artist")
        if not artist:
            continue
        by_artist.setdefault(artist, []).append(a)

    for artist, actions in by_artist.items():
        # Only delete artist cache if ALL actions are done
        if not all(a.get("status") == "done" for a in actions):
            continue

        artist_dir = Path("out") / csv_stem / artist

        if artist_dir.exists():
            logger.info(f"[apply] Retiring artist cache: {artist}")
            shutil.rmtree(artist_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
