#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from email.header import make_header
from pathlib import Path
from typing import Any

from branding import PLAYLISTARR_BANNER, PLAYLISTARR_DIVIDER, PLAYLISTARR_HEADER, PLAYLISTARR_SECTION_END
from env import PROJECT_ROOT, PROFILES_DIR

os.chdir(PROJECT_ROOT)

# ------------------------------------------------------------
# Minimal dotenv loader (silent, production-safe)
# ------------------------------------------------------------

def _load_dotenv(path: Path) -> None:
    """
    Load .env into os.environ WITHOUT printing anything.
    Does not overwrite vars already set in the environment.
    Supports basic KEY=VALUE lines and ignores comments.
    """
    if not path.exists():
        return

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()

        # Strip inline comments like: LOG_LEVEL=INFO  # comment
        if " #" in v:
            v = v.split(" #", 1)[0].rstrip()
        elif "\t#" in v:
            v = v.split("\t#", 1)[0].rstrip()

        # Optional quotes
        if (len(v) >= 2) and ((v[0] == v[-1]) and v[0] in ("'", '"')):
            v = v[1:-1]

        if k and (k not in os.environ):
            os.environ[k] = v


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
    """
    Profiles live at:
      profiles/<name>.json
      profiles/<name>.csv

    JSON minimal shape:
      {
        "label": "MuchLoud",
        "playlist_id": "PLa....",
        "rules": { ... optional ... }
      }
    """
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


def _set_run_env_from_profile(profile: Profile, args: argparse.Namespace) -> None:
    # Required run context (these unblock get_env())
    os.environ["PLAYLISTARR_ARTISTS_CSV"] = str(profile.artists_csv)
    os.environ["PLAYLISTARR_PLAYLIST_ID"] = profile.playlist_id

    # Optional flags
    os.environ["PLAYLISTARR_FORCE_UPDATE"] = "1" if args.force else "0"
    os.environ["PLAYLISTARR_NO_FILTER"] = "1" if args.no_filter else "0"
    os.environ["PLAYLISTARR_DRY_RUN"] = "1" if args.dry_run else "0"
    os.environ["PLAYLISTARR_MAX_ADD"] = str(args.max_add or 0)
    os.environ["PLAYLISTARR_PROGRESS_EVERY"] = str(args.progress_every)

    os.environ["PLAYLISTARR_VERBOSE"] = "1" if args.verbose else "0"
    os.environ["PLAYLISTARR_QUIET"] = "1" if args.quiet else "0"

    # Profile metadata (useful later)
    os.environ["PLAYLISTARR_PROFILE_NAME"] = profile.name
    os.environ["PLAYLISTARR_PROFILE_PATH"] = str(profile.profile_path)

    # Log directory per profile
    os.environ["PLAYLISTARR_RUN_LOG_DIR"] = str(Path("../logs") / profile.name)


def _set_run_env_manual(args: argparse.Namespace) -> None:
    os.environ["PLAYLISTARR_ARTISTS_CSV"] = str(Path(args.csv))
    os.environ["PLAYLISTARR_PLAYLIST_ID"] = args.playlist

    os.environ["PLAYLISTARR_FORCE_UPDATE"] = "1" if args.force else "0"
    os.environ["PLAYLISTARR_NO_FILTER"] = "1" if args.no_filter else "0"
    os.environ["PLAYLISTARR_DRY_RUN"] = "1" if args.dry_run else "0"
    os.environ["PLAYLISTARR_MAX_ADD"] = str(args.max_add or 0)
    os.environ["PLAYLISTARR_PROGRESS_EVERY"] = str(args.progress_every)

    os.environ["PLAYLISTARR_VERBOSE"] = "1" if args.verbose else "0"
    os.environ["PLAYLISTARR_QUIET"] = "1" if args.quiet else "0"

    stem = Path(args.csv).stem
    os.environ["PLAYLISTARR_RUN_LOG_DIR"] = str(Path("../logs") / stem)


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="playlistarr")
    sub = p.add_subparsers(dest="command", required=True)

    def add_common_flags(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--force", action="store_true", help="Force re-processing (discovery)")
        sp.add_argument("--no-filter", action="store_true", help="Disable filters (if supported)")
        sp.add_argument("--dry-run", action="store_true", help="Dry run where supported")
        sp.add_argument("--max-add", type=int, default=0, help="Max videos to add (0 = unlimited)")
        sp.add_argument("--progress-every", type=int, default=50, help="Progress update cadence")

        sp.add_argument("--verbose", action="store_true", help="Verbose console logs")
        sp.add_argument("--quiet", action="store_true", help="No console logs (file logs still written)")

    sync = sub.add_parser("sync", help="Run the full pipeline using a profile name")
    sync.add_argument("profile", help="Profile name (profiles/<name>.json + profiles/<name>.csv)")
    add_common_flags(sync)

    run = sub.add_parser("run", help="Run the full pipeline using explicit inputs")
    run.add_argument("--csv", required=True, help="Artist CSV path")
    run.add_argument("--playlist", required=True, help="YouTube playlist ID")
    add_common_flags(run)

    return p


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    # Load .env first (silent) so API keys etc are available.
    # But do NOT overwrite shell vars.
    _load_dotenv(PROJECT_ROOT / ".env")

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


if __name__ == "__main__":
    raise SystemExit(main())
