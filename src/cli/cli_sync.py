from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from branding import PLAYLISTARR_BANNER, PLAYLISTARR_HEADER
from env import PROFILES_DIR


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


def _set_common_run_env(args: argparse.Namespace) -> None:
    os.environ["PLAYLISTARR_FORCE_UPDATE"] = "1" if args.force else "0"
    os.environ["PLAYLISTARR_NO_FILTER"] = "1" if args.no_filter else "0"
    os.environ["PLAYLISTARR_DRY_RUN"] = "1" if args.dry_run else "0"
    os.environ["PLAYLISTARR_MAX_ADD"] = str(args.max_add or 0)
    os.environ["PLAYLISTARR_PROGRESS_EVERY"] = str(args.progress_every)

    os.environ["PLAYLISTARR_VERBOSE"] = "1" if args.verbose else "0"
    os.environ["PLAYLISTARR_QUIET"] = "1" if args.quiet else "0"


def _set_run_env_from_profile(profile: Profile, args: argparse.Namespace) -> None:
    os.environ["PLAYLISTARR_ARTISTS_CSV"] = str(profile.artists_csv)
    os.environ["PLAYLISTARR_PLAYLIST_ID"] = profile.playlist_id

    _set_common_run_env(args)

    os.environ["PLAYLISTARR_PROFILE_NAME"] = profile.name
    os.environ["PLAYLISTARR_PROFILE_PATH"] = str(profile.profile_path)

    # Log directory per profile (preserving your layout)
    os.environ["PLAYLISTARR_RUN_LOG_DIR"] = str(Path("../logs") / profile.name)


def _set_run_env_manual(args: argparse.Namespace) -> None:
    os.environ["PLAYLISTARR_ARTISTS_CSV"] = str(Path(args.csv))
    os.environ["PLAYLISTARR_PLAYLIST_ID"] = args.playlist

    _set_common_run_env(args)

    stem = Path(args.csv).stem
    os.environ["PLAYLISTARR_RUN_LOG_DIR"] = str(Path("../logs") / stem)


# ------------------------------------------------------------
# Parser
# ------------------------------------------------------------

def build_sync_parser(subparsers: argparse._SubParsersAction) -> None:
    def add_common_flags(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--force", action="store_true", help="Force re-processing (discovery)")
        sp.add_argument("--no-filter", action="store_true", help="Disable filters (if supported)")
        sp.add_argument("--dry-run", action="store_true", help="Dry run where supported")
        sp.add_argument("--max-add", type=int, default=0, help="Max videos to add (0 = unlimited)")
        sp.add_argument("--progress-every", type=int, default=50, help="Progress update cadence")

        sp.add_argument("--verbose", action="store_true", help="Verbose console logs")
        sp.add_argument("--quiet", action="store_true", help="No console logs (file logs still written)")

    sync = subparsers.add_parser("sync", help="Run the full pipeline using a profile name")
    sync.add_argument("profile", help="Profile name (profiles/<name>.json + profiles/<name>.csv)")
    add_common_flags(sync)

    run = subparsers.add_parser("run", help="Run the full pipeline using explicit inputs")
    run.add_argument("--csv", required=True, help="Artist CSV path")
    run.add_argument("--playlist", required=True, help="YouTube playlist ID")
    add_common_flags(run)


# ------------------------------------------------------------
# Handler
# ------------------------------------------------------------

def handle_sync(args: argparse.Namespace) -> int:
    # Set PLAYLISTARR_* env vars before importing anything else
    if args.command == "sync":
        profile = _load_profile(args.profile)
        _set_run_env_from_profile(profile, args)
    elif args.command == "run":
        _set_run_env_manual(args)
    else:
        raise RuntimeError(f"Unknown command: {args.command}")

    # Now it's safe to import modules that call get_env()/init_logging().
    from logger import init_logging, get_logger
    from runner import run_once, RunResult

    init_logging()
    log = get_logger("playlistarr")

    log.info(PLAYLISTARR_BANNER)
    log.info("Playlistarr starting")
    log.info(f"Command: {args.command}")

    log.info(PLAYLISTARR_HEADER("Bootstrap Scripts"))

    if args.command == "sync":
        log.info(f"Profile: {os.environ.get('PLAYLISTARR_PROFILE_NAME')}")
        log.info(f"CSV: {os.environ.get('PLAYLISTARR_ARTISTS_CSV')}")
        log.info(f"Playlist: {os.environ.get('PLAYLISTARR_PLAYLIST_ID')}")
    else:
        log.info(f"CSV: {os.environ.get('PLAYLISTARR_ARTISTS_CSV')}")
        log.info(f"Playlist: {os.environ.get('PLAYLISTARR_PLAYLIST_ID')}")

    result = run_once()

    # Exit codes (stable for automation / docker health scripting)
    if result.overall == RunResult.OK:
        log.info("Done: OK")
        return 0

    if result.overall == RunResult.API_QUOTA:
        log.warning("Done: stopped due to API key quota exhaustion")
        return 10

    if result.overall == RunResult.OAUTH_QUOTA:
        log.warning("Done: stopped due to OAuth quota exhaustion")
        return 11

    if result.overall == RunResult.AUTH_INVALID:
        log.error("Done: OAuth invalid (reauth required)")
        return 12

    log.error("Done: failed")
    return 20
