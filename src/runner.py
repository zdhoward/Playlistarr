from __future__ import annotations

import csv
import os
import subprocess
import sys
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional
import re

from branding import PLAYLISTARR_HEADER, PLAYLISTARR_SECTION_END
from env import PROJECT_ROOT, get_env
from logger import get_logger

log = get_logger("playlistarr.runner")


class RunResult(str, Enum):
    OK = "ok"
    QUOTA_EXHAUSTED = "quota_exhausted"
    AUTH_INVALID = "auth_invalid"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class StageResult:
    name: str
    state: RunResult
    exit_code: int
    reason: Optional[str] = None


@dataclass(frozen=True)
class RunOutcome:
    overall: RunResult
    stages: list[StageResult]


_STAGES: list[tuple[str, list[str]]] = [
    ("Discovery", [sys.executable, "-m", "discover_music_videos"]),
    ("Invalidation (Plan)", [sys.executable, "-m", "playlist_invalidate"]),
    ("Invalidation (Apply)", [sys.executable, "-m", "playlist_apply_invalidation"]),
    ("Sync", [sys.executable, "-m", "youtube_playlist_sync"]),
]


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------


def _count_artists(csv_path: Path) -> int:
    count = 0
    saw_header = False
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            v = (row[0] or "").strip()
            if not v:
                continue
            if not saw_header:
                saw_header = True
                if v.lower() == "artist":
                    continue
            count += 1
    return count


def _infer_state(exit_code: int, tail: str) -> RunResult:
    if exit_code == 0:
        return RunResult.OK
    if exit_code == 10:
        return RunResult.QUOTA_EXHAUSTED
    if exit_code == 12:
        return RunResult.AUTH_INVALID

    t = tail.lower()
    if "quota" in t:
        return RunResult.QUOTA_EXHAUSTED
    if "auth_invalid" in t or "reauth" in t:
        return RunResult.AUTH_INVALID

    return RunResult.FAILED


def _log_header(title: str) -> None:
    log.info(PLAYLISTARR_HEADER(title).rstrip("\n"))


def _log_footer() -> None:
    log.info(PLAYLISTARR_SECTION_END())


_CHILD_LEVEL_RE = re.compile(
    r"""
    ^\s*
    (?:
        \[\s*(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s*\]
        |
        (DEBUG|INFO|WARNING|ERROR|CRITICAL)
    )
    \s+
    (.*\S)?\s*$
    """,
    re.VERBOSE,
)

_LEVEL_MAP: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def _parse_child_level(line: str) -> tuple[int | None, str]:
    m = _CHILD_LEVEL_RE.match(line)
    if not m:
        return None, line.rstrip()

    lvl = (m.group(1) or m.group(2) or "").upper()
    rest = (m.group(3) or "").rstrip()
    return _LEVEL_MAP.get(lvl), rest


# ------------------------------------------------------------
# Core execution
# ------------------------------------------------------------


def _run_stage(
    *,
    index: int,
    total: int,
    name: str,
    argv: list[str],
    csv_path: Path,
    playlist_id: str,
    verbose: bool,
    quiet: bool,
) -> StageResult:
    # --------------------------------------------------------
    # Subprocess environment (CRITICAL FIX)
    # --------------------------------------------------------

    env = os.environ.copy()

    # 🔑 HARD REQUIRE: API keys must propagate to child processes
    if "YOUTUBE_API_KEYS" not in env or not env["YOUTUBE_API_KEYS"].strip():
        raise RuntimeError(
            "YOUTUBE_API_KEYS is missing from environment before launching pipeline stage"
        )

    env.setdefault("PLAYLISTARR_ARTISTS_CSV", str(csv_path))
    env.setdefault("PLAYLISTARR_PLAYLIST_ID", playlist_id)
    env["PLAYLISTARR_VERBOSE"] = "1" if verbose else "0"
    env["PLAYLISTARR_QUIET"] = "1" if quiet else "0"

    if not quiet:
        _log_header(f"Stage {index}/{total}: {name}")

    proc = subprocess.Popen(
        argv + [str(csv_path), playlist_id],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    tail_lines: list[str] = []

    assert proc.stdout is not None
    for raw in proc.stdout:
        line = raw.rstrip("\n")
        if not line:
            continue

        tail_lines.append(line)

        if not quiet:
            level, msg = _parse_child_level(line)
            if level is None:
                log.info(msg, extra={"passthrough": True})
            else:
                log.log(level, msg, extra={"passthrough": True})

    exit_code = proc.wait()
    tail = "\n".join(tail_lines[-200:])
    state = _infer_state(exit_code, tail)

    if not quiet:
        _log_header(f"Stage {index} END: {name} ({state.value})")
        _log_footer()

    return StageResult(name=name, state=state, exit_code=exit_code)


def run_once(
    *,
    profile: str | None = None,
    csv_path: str | Path | None = None,
    playlist_id: str | None = None,
    verbose: bool | None = None,
    quiet: bool | None = None,
) -> RunOutcome:
    env = get_env()

    resolved_csv = Path(csv_path) if csv_path else Path(env.artists_csv)
    resolved_playlist = playlist_id or env.playlist_id

    ctx_verbose = bool(verbose) if verbose is not None else env.verbose
    ctx_quiet = bool(quiet) if quiet is not None else env.quiet

    results: list[StageResult] = []
    overall: RunResult = RunResult.OK
    block_reason: Optional[str] = None

    for i, (name, argv) in enumerate(_STAGES, start=1):
        if block_reason is not None:
            results.append(
                StageResult(
                    name=name,
                    state=RunResult.SKIPPED,
                    exit_code=-1,
                    reason=f"blocked_by_{block_reason}",
                )
            )
            continue

        r = _run_stage(
            index=i,
            total=len(_STAGES),
            name=name,
            argv=argv,
            csv_path=resolved_csv,
            playlist_id=resolved_playlist,
            verbose=ctx_verbose,
            quiet=ctx_quiet,
        )
        results.append(r)

        if r.state != RunResult.OK:
            overall = r.state
            block_reason = r.state.value

    return RunOutcome(overall=overall, stages=results)
