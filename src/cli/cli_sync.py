from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path

from branding import PLAYLISTARR_BANNER, PLAYLISTARR_HEADER
from env import PROFILES_DIR, reset_env_caches


@dataclass(frozen=True)
class Profile:
    name: str
    profile_path: Path
    artists_csv: Path
    playlist_id: str


def _load_profile(name: str) -> Profile:
    profile_path = PROFILES_DIR / f"{name}.json"
    artists_csv = PROFILES_DIR / f"{name}.csv"

    if not profile_path.exists():
        raise RuntimeError(f"Profile '{name}' does not exist")

    data = json.loads(profile_path.read_text(encoding="utf-8"))
    playlist_id = str(data.get("playlist_id") or "").strip()
    if not playlist_id:
        raise RuntimeError(f"Profile '{name}' missing playlist_id")

    return Profile(name, profile_path, artists_csv, playlist_id)


def build_sync_parser(subparsers: argparse._SubParsersAction) -> None:
    sync = subparsers.add_parser("sync", help="Run the full pipeline")
    sync.add_argument("profile")

    # These MUST live on the sync subcommand so:
    #   playlistarr sync muchloud --verbose
    # keeps working.
    sync.add_argument("--verbose", action="store_true", help="Enable debug logging")
    sync.add_argument("--quiet", action="store_true", help="Reduce console output")

    sync.set_defaults(_handler=handle_sync)


def handle_sync(args: argparse.Namespace) -> int:
    profile = _load_profile(args.profile)

    os.environ.update(
        {
            "PLAYLISTARR_PROFILE_NAME": profile.name,
            "PLAYLISTARR_PROFILE_PATH": str(profile.profile_path),
            "PLAYLISTARR_ARTISTS_CSV": str(profile.artists_csv),
            "PLAYLISTARR_PLAYLIST_ID": profile.playlist_id,
            "PLAYLISTARR_VERBOSE": "1" if args.verbose else "0",
            "PLAYLISTARR_QUIET": "1" if args.quiet else "0",
        }
    )

    # CLI handlers mutate os.environ; ensure env views are rebuilt.
    reset_env_caches()

    from logger import init_logging, get_logger
    from runner import run_once, RunResult

    # Re-apply logging now that env flags are set
    init_logging(module="sync", profile=profile.name)
    log = get_logger("playlistarr")

    log.info(PLAYLISTARR_BANNER)
    log.info("Playlistarr starting")
    log.info("Command: sync")
    log.info(PLAYLISTARR_HEADER("Bootstrap Scripts"))

    log.info(f"Profile: {profile.name}")
    log.info(f"CSV: {profile.artists_csv}")
    log.info(f"Playlist: {profile.playlist_id}")

    result = run_once()

    log.info("")
    log.info("Run summary:")
    for stage in result.stages:
        log.info(f"  - {stage.name}: {stage.state.value}")

    if result.overall == RunResult.OK:
        return 0
    if result.overall == RunResult.QUOTA_EXHAUSTED:
        return 10
    if result.overall == RunResult.AUTH_INVALID:
        return 12
    return 20
