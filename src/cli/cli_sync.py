from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from branding import PLAYLISTARR_BANNER, PLAYLISTARR_HEADER
from env import PROFILES_DIR, get_env


# ------------------------------------------------------------
# Profiles
# ------------------------------------------------------------


@dataclass(frozen=True)
class Profile:
    name: str
    profile_path: Path
    artists_csv: Path
    playlist_id: str
    rules: dict[str, Any]


def _load_profile(name: str) -> Profile:
    profile_path = PROFILES_DIR / f"{name}.json"
    csv_path = PROFILES_DIR / f"{name}.csv"

    if not profile_path.exists():
        raise FileNotFoundError(f"Missing profile JSON: {profile_path}")

    if not csv_path.exists():
        raise FileNotFoundError(f"Missing profile CSV: {csv_path}")

    data = json.loads(profile_path.read_text(encoding="utf-8"))

    playlist_id = (data.get("playlist_id") or "").strip()
    if not playlist_id:
        raise ValueError(f"Profile {name} missing required field: playlist_id")

    rules = data.get("rules") or {}

    return Profile(
        name=name,
        profile_path=profile_path,
        artists_csv=csv_path,
        playlist_id=playlist_id,
        rules=rules,
    )


# ------------------------------------------------------------
# Parser
# ------------------------------------------------------------


def build_sync_parser(subparsers: argparse._SubParsersAction) -> None:
    sync = subparsers.add_parser(
        "sync", help="Run the full pipeline using a profile name"
    )

    sync.add_argument("profile", help="Profile name")
    sync.add_argument("--force", action="store_true")
    sync.add_argument("--no-filter", action="store_true")
    sync.add_argument("--dry-run", action="store_true")
    sync.add_argument("--max-add", type=int, default=0)
    sync.add_argument("--progress-every", type=int, default=50)
    sync.add_argument("--verbose", action="store_true")
    sync.add_argument("--quiet", action="store_true")


# ------------------------------------------------------------
# Handler
# ------------------------------------------------------------


def handle_sync(args: argparse.Namespace) -> int:
    profile = _load_profile(args.profile)

    # Environment is the configuration boundary for the pipeline
    os.environ["PLAYLISTARR_PROFILE_NAME"] = profile.name
    os.environ["PLAYLISTARR_PROFILE_PATH"] = str(profile.profile_path)
    os.environ["PLAYLISTARR_ARTISTS_CSV"] = str(profile.artists_csv)
    os.environ["PLAYLISTARR_PLAYLIST_ID"] = profile.playlist_id
    os.environ["PLAYLISTARR_VERBOSE"] = "1" if args.verbose else "0"
    os.environ["PLAYLISTARR_QUIET"] = "1" if args.quiet else "0"
    os.environ["PLAYLISTARR_MAX_ADD"] = str(args.max_add or 0)
    os.environ["PLAYLISTARR_PROGRESS_EVERY"] = str(args.progress_every)

    from logger import init_logging, get_logger
    from runner import run_once, RunResult

    init_logging()
    log = get_logger("playlistarr")

    log.info(PLAYLISTARR_BANNER)
    log.info("Playlistarr starting")
    log.info("Command: sync")
    log.info(PLAYLISTARR_HEADER("Bootstrap Scripts"))

    log.info(f"Profile: {profile.name}")
    log.info(f"CSV: {profile.artists_csv}")
    log.info(f"Playlist: {profile.playlist_id}")

    # Force env resolution early so auth / provider config errors surface cleanly
    _ = get_env()

    result = run_once()

    # --------------------------------------------------
    # Run summary (explicit, non-interactive safe)
    # --------------------------------------------------

    log.info("")
    log.info("Run summary:")
    for stage in result.stages:
        if stage.state == RunResult.SKIPPED:
            log.info(f"  - {stage.name}: skipped ({stage.reason})")
        else:
            log.info(f"  - {stage.name}: {stage.state.value}")
    log.info("")

    # -----------------------------
    # Terminal state handling
    # -----------------------------

    if result.overall == RunResult.OK:
        log.info("Done: OK (playlist fully up to date)")
        return 0

    if result.overall == RunResult.QUOTA_EXHAUSTED:
        log.warning("Done: quota exhausted (playlist may be incomplete)")
        return 10

    if result.overall == RunResult.AUTH_INVALID:
        log.error("Done: OAuth invalid (reauth required)")
        return 12

    log.error("Done: failed")
    return 20
