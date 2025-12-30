#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from email.header import make_header
from enum import Enum
from pathlib import Path
from typing import Optional
from branding import PLAYLISTARR_BANNER, PLAYLISTARR_DIVIDER, PLAYLISTARR_HEADER, PLAYLISTARR_SECTION_END


from logger import get_logger


logger = get_logger("runner")


class RunResult(Enum):
    OK = "ok"
    API_QUOTA = "api_quota"
    OAUTH_QUOTA = "oauth_quota"
    AUTH_INVALID = "auth_invalid"
    FAILED = "failed"


@dataclass
class StepResult:
    name: str
    exit_code: int
    seconds: float
    stopped_pipeline: bool = False
    note: str = ""


@dataclass
class RunSummary:
    overall: RunResult
    steps: list[StepResult]


def _project_root() -> Path:
    return Path(__file__).resolve().parent


def _py() -> str:
    return sys.executable


def _run_script(
    script: str,
    args: list[str] | None = None,
    *,
    name: str,
    stop_on_codes: set[int] | None = None,
    allow_fail: bool = False,
) -> StepResult:
    """
    Run a single python script in a subprocess.
    Returns exit code + duration.

    stop_on_codes:
      if the script returns one of these exit codes, we mark stopped_pipeline=True.
    """
    if args is None:
        args = []
    if stop_on_codes is None:
        stop_on_codes = set()

    cmd = [_py(), str(_project_root() / script), *args]

    start = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(_project_root()),
            env=os.environ.copy(),
            text=True,
        )
        code = int(proc.returncode)
    except FileNotFoundError:
        return StepResult(name=name, exit_code=127, seconds=time.time() - start, stopped_pipeline=True, note=f"Missing script: {script}")
    except Exception as e:
        return StepResult(name=name, exit_code=1, seconds=time.time() - start, stopped_pipeline=True, note=f"Runner exception: {e}")

    dur = time.time() - start

    stopped = code in stop_on_codes
    note = ""

    if stopped:
        note = "Stop condition triggered"
    elif (code != 0) and allow_fail:
        note = "Non-zero exit (allowed)"
    elif code != 0:
        note = "Non-zero exit"

    return StepResult(name=name, exit_code=code, seconds=dur, stopped_pipeline=stopped, note=note)


def _log_step_banner(title: str) -> None:
    logger.info("")
    logger.info("=" * 44)
    logger.info(title)
    logger.info("=" * 44)


def _log_step_summary(step: StepResult) -> None:
    msg = f"{step.name}: exit={step.exit_code} ({step.seconds:.1f}s)"

    if step.exit_code == 0:
        logger.info(msg)
        return

    if step.note:
        msg = f"{msg} — {step.note}"

    # Clean quota exits should be warnings, not errors
    if (
        step.exit_code in (2, 10, 11, 12)
        or (step.name in ("invalidate_apply", "sync") and step.exit_code == 1)
        or (step.name == "discover" and step.exit_code == 1)
    ):
        logger.warning(msg)
    else:
        logger.error(msg)


def run_once() -> RunSummary:
    """
    Orchestrate a single pipeline run.
    Expects PLAYLISTARR_* env vars already set (by playlistarr.py).
    """
    steps: list[StepResult] = []

    artists_csv = os.environ.get("PLAYLISTARR_ARTISTS_CSV", "")
    playlist_id = os.environ.get("PLAYLISTARR_PLAYLIST_ID", "")

    if not artists_csv or not playlist_id:
        logger.error("Missing required env vars: PLAYLISTARR_ARTISTS_CSV / PLAYLISTARR_PLAYLIST_ID")
        return RunSummary(overall=RunResult.FAILED, steps=[])

    # ------------------------------------------------------------
    # 0) OAuth Health Check
    # ------------------------------------------------------------
    logger.info(PLAYLISTARR_HEADER("OAuth Health Check"))
    oauth = _run_script(
        "oauth_health_check.py",
        name="oauth_health_check",
        # Treat "reauth required" as a hard stop if your script uses exit=2 for that
        stop_on_codes={2},
        allow_fail=False,
    )
    steps.append(oauth)
    _log_step_summary(oauth)

    if oauth.exit_code == 2:
        # OAuth invalid/expired and reauth didn't succeed
        return RunSummary(overall=RunResult.AUTH_INVALID, steps=steps)

    # Note: if oauth_health_check returns "quota exhausted but oauth valid" as 0, continue.

    # ------------------------------------------------------------
    # 1) Discovery
    # ------------------------------------------------------------
    logger.info(PLAYLISTARR_HEADER("Discovery"))
    discovery = _run_script(
        "discover_music_videos.py",
        name="discover",
        # If discovery returns 2 for API key quota exhaustion, we stop discovery but keep going.
        stop_on_codes=set(),
        allow_fail=True,
    )
    steps.append(discovery)
    _log_step_summary(discovery)

    # ------------------------------------------------------------
    # 2) Invalidation Plan
    # ------------------------------------------------------------
    logger.info(PLAYLISTARR_HEADER("Invalidation (plan)"))
    inv_plan = _run_script(
        "playlist_invalidate.py",
        name="invalidate_plan",
        allow_fail=False,
    )
    steps.append(inv_plan)
    _log_step_summary(inv_plan)

    if inv_plan.exit_code != 0:
        return RunSummary(overall=RunResult.FAILED, steps=steps)

    # ------------------------------------------------------------
    # 3) Invalidation Apply (OAuth mutations)
    # ------------------------------------------------------------
    logger.info(PLAYLISTARR_HEADER("Invalidation (apply)"))
    inv_apply = _run_script(
        "playlist_apply_invalidation.py",
        name="invalidate_apply",
        # If apply hits OAuth quota, it should exit with 2 (or your chosen code).
        stop_on_codes={2},
        allow_fail=True,
    )
    steps.append(inv_apply)
    _log_step_summary(inv_apply)

    if inv_apply.exit_code == 2:
        return RunSummary(overall=RunResult.OAUTH_QUOTA, steps=steps)

    if inv_apply.exit_code not in (0, 2):
        # non-zero, non-quota
        return RunSummary(overall=RunResult.FAILED, steps=steps)

    # ------------------------------------------------------------
    # 4) Cleanup (should never kill the pipeline)
    #    Your cleanup currently still requires args, so we pass them.
    # ------------------------------------------------------------
    logger.info(PLAYLISTARR_HEADER("Cleanup"))
    cleanup_args = [artists_csv, playlist_id]
    # Preserve previous default: apply deletions only if not dry-run
    if os.environ.get("PLAYLISTARR_DRY_RUN", "0") != "1":
        cleanup_args.append("--apply")

    cleanup = _run_script(
        "cleanup.py",
        args=cleanup_args,
        name="cleanup",
        allow_fail=True,
    )
    steps.append(cleanup)
    _log_step_summary(cleanup)

    # ------------------------------------------------------------
    # 5) Playlist Sync (OAuth mutations)
    # ------------------------------------------------------------
    logger.info(PLAYLISTARR_HEADER("Playlist Sync"))
    sync = _run_script(
        "youtube_playlist_sync.py",
        name="sync",
        stop_on_codes={2},
        allow_fail=True,
    )
    steps.append(sync)
    _log_step_summary(sync)

    if sync.exit_code == 2:
        return RunSummary(overall=RunResult.OAUTH_QUOTA, steps=steps)

    # ------------------------------------------------------------
    # Overall summary
    # ------------------------------------------------------------
    logger.info(PLAYLISTARR_HEADER("Run Summary"))

    def _is_clean_quota_stop(s: StepResult) -> bool:
        # OAuth quota
        if s.name in ("invalidate_apply", "sync") and s.exit_code == 1:
            return True

        # API key quota (discovery)
        if s.name == "discover" and s.exit_code == 1:
            return True

        return False

    ok = True
    for s in steps:
        if s.exit_code == 0:
            continue
        if _is_clean_quota_stop(s):
            continue
        if s.name == "cleanup":
            continue
        ok = False
        break

    if ok:
        if any(_is_clean_quota_stop(s) for s in steps):
            logger.warning("Overall: STOPPED BY QUOTA")
            if any(s.name == "sync" for s in steps if _is_clean_quota_stop(s)):
                return RunSummary(overall=RunResult.OAUTH_QUOTA, steps=steps)
            return RunSummary(overall=RunResult.API_QUOTA, steps=steps)

        logger.info("Overall: OK")
        return RunSummary(overall=RunResult.OK, steps=steps)

    logger.error("Overall: FAILED")
    return RunSummary(overall=RunResult.FAILED, steps=steps)

