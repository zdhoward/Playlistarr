#!/usr/bin/env python3

from __future__ import annotations

import shutil
from pathlib import Path

from env import get_env
from utils import canonicalize_artist
from logger import init_logging, get_logger

# ----------------------------
# Environment
# ----------------------------
env = get_env()

# ----------------------------
# Logging
# ----------------------------
init_logging()
logger = get_logger(__name__)


# ============================================================
# Helpers
# ============================================================


def read_artists(csv_path: Path) -> list[str]:
    artists = []
    with csv_path.open("r", encoding="utf-8") as f:
        for line in f:
            name = line.strip()
            if name:
                artists.append(name)
    return artists


def get_out_root(csv_path: Path) -> Path:
    return Path("../out") / csv_path.stem


def scan_orphans(out_root: Path, allowed_keys: set[str]):
    if not out_root.exists():
        return []

    orphans = []
    for artist_dir in out_root.iterdir():
        if not artist_dir.is_dir():
            continue

        folder_key = artist_dir.name
        if folder_key not in allowed_keys:
            orphans.append(artist_dir)

    return orphans


# ============================================================
# Main
# ============================================================


def main() -> int:
    csv_path = Path(env.artists_csv)
    playlist_id = env.playlist_id
    apply = not env.dry_run

    if not csv_path.exists():
        logger.error(f"CSV not found: {csv_path}")
        return 1

    logger.debug(f"Playlistarr cleanup for playlist: {playlist_id}")
    logger.debug(f"CSV: {csv_path}")

    # Read display names
    display_artists = read_artists(csv_path)

    # Canonicalize them into keys
    allowed_keys = {
        canonicalize_artist(name)
        for name in display_artists
        if canonicalize_artist(name)
    }

    out_root = get_out_root(csv_path)

    logger.debug(f"Discovery root: {out_root}")
    logger.debug(f"Artists in CSV: {len(display_artists)}")
    logger.debug(f"Canonical keys: {len(allowed_keys)}")

    orphans = scan_orphans(out_root, allowed_keys)

    if not orphans:
        logger.debug("No orphaned artist caches found.")
        return 0

    logger.debug(f"Orphaned artist caches ({len(orphans)}):")
    for p in orphans:
        logger.debug(f" - {p.name}")

    if not apply:
        logger.debug("DRY RUN - no files deleted.")
        return 0

    logger.debug("Deleting orphaned artist caches...")
    for p in orphans:
        logger.debug(f"Deleting {p}")
        shutil.rmtree(p, ignore_errors=True)

    logger.debug("Cleanup complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
