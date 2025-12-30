#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from branding import PLAYLISTARR_BANNER
from env import get_env
from logger import get_logger
from ui import InteractiveUI
from ui_events import try_parse_ui_event

logger = get_logger("runner")


# ============================================================================
# Models
# ============================================================================


class RunResult(Enum):
    OK = "completed"          # ran fully, up-to-date
    API_QUOTA = "api_quota"   # controlled stop (discovery quota)
    OAUTH_QUOTA = "oauth_quota"  # controlled stop (oauth quota)
    AUTH_INVALID = "auth_invalid"  # action required
    FAILED = "failed"         # unexpected failure


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


# ============================================================================
# Helpers
# ============================================================================


def _project_root() -> Path:
    return Path(__file__).resolve().parent


def _py() -> str:
    return sys.executable


def _stage_status(stage_name: str, exit_code: int) -> str:
    """
    UI-only stage status mapping.

    Important nuance:
      - oauth_health_check.py uses exit_code 2 => AUTH INVALID
      - mutation stages (apply/sync) use exit_code 2 => OAUTH QUOTA
      - exit_code 1 => quota exhausted (API keys) in your pipeline
    """
    if exit_code == 0:
        return "completed"
    if exit_code == 1:
        return "quota_exhausted"

    if exit_code == 2:
        if stage_name.lower().startswith("oauth health"):
            return "auth_invalid"
        return "quota_exhausted"

    return "failed"


# ============================================================================
# Script runners
# ============================================================================


def _run_script(
    script: str,
    args: list[str] | None = None,
    *,
    name: str,
    stop_on_codes: set[int] | None = None,
    allow_fail: bool = False,
) -> StepResult:
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
    except Exception as e:
        # This is a runner failure (not a stage exit code)
        return StepResult(name, 99, time.time() - start, True, str(e))

    dur = time.time() - start
    stopped = code in stop_on_codes

    return StepResult(name, code, dur, stopped)


def _run_script_interactive(
    script: str,
    *,
    name: str,
    ui: InteractiveUI,
    args: list[str] | None = None,
    stop_on_codes: set[int] | None = None,
    allow_fail: bool = False,
) -> StepResult:
    if args is None:
        args = []
    if stop_on_codes is None:
        stop_on_codes = set()

    # Force UI mode for subprocesses
    env = os.environ.copy()
    env["PLAYLISTARR_UI"] = "1"
    env["PLAYLISTARR_QUIET"] = "1"
    env["PLAYLISTARR_VERBOSE"] = "0"

    cmd = [_py(), str(_project_root() / script), *args]
    start = time.time()
    last_line: Optional[str] = None

    proc = subprocess.Popen(
        cmd,
        cwd=str(_project_root()),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    assert proc.stdout is not None

    try:
        for raw in proc.stdout:
            line = raw.rstrip("\n")
            if not line:
                continue

            evt = try_parse_ui_event(line)
            if evt:
                _apply_ui_event(ui, evt)
                ui.render()
                continue

            last_line = line
            logger.debug(f"[{name}] {line}")
    except Exception as e:
        # If we blow up reading stdout, try to stop the child and return a runner failure code.
        try:
            proc.kill()
        except Exception:
            pass
        dur = time.time() - start
        return StepResult(name, 99, dur, True, f"interactive read failed: {e}")

    code = int(proc.wait())
    dur = time.time() - start
    stopped = code in stop_on_codes
    note = last_line or ""

    return StepResult(name, code, dur, stopped, note)


def _apply_ui_event(ui: InteractiveUI, evt: dict) -> None:
    event = evt.get("event")

    if event == "stage_start":
        ui.set_stage(evt.get("stage", ""), index=evt.get("index", 0), total=evt.get("total", 0))
        ui.set_task(evt.get("task", ""))
        return

    if event == "artist_start":
        ui.set_artist(evt.get("artist", ""))
        ui.set_task(evt.get("task", ""))
        ui.set_counts(old=evt.get("old"), new=evt.get("new"))
        ui.set_api_key(index=evt.get("api_key_index"), total=evt.get("api_key_total"))
        return

    if event == "artist_done":
        ui.push_history(evt.get("artist", ""))
        ui.set_progress(completed=evt.get("index"))
        return

    if event == "detail":
        ui.push_detail(evt.get("line", ""), style=evt.get("style", "dim"))


# ============================================================================
# Orchestrator
# ============================================================================


def run_once() -> RunSummary:
    env = get_env()
    interactive = env.interactive

    ui: Optional[InteractiveUI] = None
    steps: list[StepResult] = []

    # The single source of truth for final outcome.
    # Must be set before every return path; also finalized in `finally`.
    final_result: RunResult = RunResult.FAILED

    def run_stage(**kw) -> StepResult:
        nonlocal ui
        if interactive:
            assert ui is not None
            return _run_script_interactive(ui=ui, **kw)
        return _run_script(**kw)

    try:
        if interactive:
            ui = InteractiveUI()
            ui.start()
            ui.push_detail(PLAYLISTARR_BANNER.strip(), style="bold")
            ui.render(force=True)

        # ------------------------------------------------------------
        # OAuth Health
        # ------------------------------------------------------------
        oauth = run_stage(script="oauth_health_check.py", name="OAuth Health Check", stop_on_codes={2})
        steps.append(oauth)
        if ui:
            ui.mark_stage("OAuth Health Check", _stage_status("OAuth Health Check", oauth.exit_code))

        if oauth.exit_code == 2:
            final_result = RunResult.AUTH_INVALID
            return RunSummary(final_result, steps)

        if oauth.exit_code != 0:
            final_result = RunResult.FAILED
            return RunSummary(final_result, steps)

        # ------------------------------------------------------------
        # Discovery (API keys)
        # ------------------------------------------------------------
        disc = run_stage(script="discover_music_videos.py", name="Discovery", allow_fail=True)
        steps.append(disc)
        if ui:
            ui.mark_stage("Discovery", _stage_status("Discovery", disc.exit_code))

        # If discovery returns quota exhausted (1), that's a controlled stop.
        # We still might have already produced partial outputs for later stages;
        # but your pipeline has always allowed discovery to stop safely.
        if disc.exit_code == 1:
            final_result = RunResult.API_QUOTA
            return RunSummary(final_result, steps)

        if disc.exit_code != 0:
            final_result = RunResult.FAILED
            return RunSummary(final_result, steps)

        # ------------------------------------------------------------
        # Invalidate Plan
        # ------------------------------------------------------------
        invp = run_stage(script="playlist_invalidate.py", name="Invalidation Plan")
        steps.append(invp)
        if ui:
            ui.mark_stage("Invalidation Plan", _stage_status("Invalidation Plan", invp.exit_code))

        if invp.exit_code != 0:
            final_result = RunResult.FAILED
            return RunSummary(final_result, steps)

        # ------------------------------------------------------------
        # Invalidate Apply (OAuth mutation)
        # ------------------------------------------------------------
        inva = run_stage(
            script="playlist_apply_invalidation.py",
            name="Invalidation Apply",
            stop_on_codes={2},
            allow_fail=True,
        )
        steps.append(inva)
        if ui:
            ui.mark_stage("Invalidation Apply", _stage_status("Invalidation Apply", inva.exit_code))

        # In your current pipeline, apply uses exit_code 2 for OAuth quota exhaustion
        if inva.exit_code == 2:
            final_result = RunResult.OAUTH_QUOTA
            return RunSummary(final_result, steps)

        if inva.exit_code != 0:
            final_result = RunResult.FAILED
            return RunSummary(final_result, steps)

        # ------------------------------------------------------------
        # Playlist Sync (OAuth mutation)
        # ------------------------------------------------------------
        sync = run_stage(
            script="youtube_playlist_sync.py",
            name="Playlist Sync",
            stop_on_codes={2},
            allow_fail=True,
        )
        steps.append(sync)
        if ui:
            ui.mark_stage("Playlist Sync", _stage_status("Playlist Sync", sync.exit_code))

        if sync.exit_code == 2:
            final_result = RunResult.OAUTH_QUOTA
            return RunSummary(final_result, steps)

        if sync.exit_code != 0:
            final_result = RunResult.FAILED
            return RunSummary(final_result, steps)

        final_result = RunResult.OK
        return RunSummary(final_result, steps)

    except KeyboardInterrupt:
        # Still emit RUN_STATUS and close UI in finally.
        final_result = RunResult.FAILED
        raise

    except Exception:
        # Still emit RUN_STATUS and close UI in finally.
        final_result = RunResult.FAILED
        raise

    finally:
        # Persist final run status to log (machine-readable, exactly once).
        # This MUST happen regardless of early returns or exceptions.
        try:
            logger.info(f"RUN_STATUS={final_result.value}")
        except Exception:
            pass

        if ui:
            try:
                ui.summary.stop_reason = final_result.value
                ui.stop()
                ui.print_summary()
            except Exception:
                pass
