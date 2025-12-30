from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Iterable
import os

from env import PROJECT_ROOT


# ----------------------------
# Help dispatch (subparser-local)
# ----------------------------


def dispatch_subparser_help(
    parser: argparse.ArgumentParser, path: list[str] | None
) -> int:
    """
    Implements consistent `X help [subcmd ...]` behavior for a subtree parser.
    """
    if not path:
        parser.print_help()
        return 0

    try:
        parser.parse_args(path + ["--help"])
    except SystemExit:
        pass
    return 0


# ----------------------------
# Logs / runs filesystem helpers
# ----------------------------


def resolve_log_dir(*, profile: str | None, explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()

    base = (PROJECT_ROOT / "logs").resolve()
    return (base / profile).resolve() if profile else base


def iter_log_files(log_dir: Path) -> Iterable[Path]:
    if not log_dir.exists():
        return []
    return (p for p in log_dir.iterdir() if p.is_file() and p.suffix == ".log")


def find_log_file(log_dir: Path, name: str) -> Path | None:
    if not log_dir.exists():
        return None

    candidates = [
        log_dir / name,
        log_dir / f"{name}.log",
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            return p

    for p in log_dir.glob("*.log"):
        if p.stem == name:
            return p

    return None


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _print_tail_impl(path: Path, lines: int) -> None:
    try:
        data = read_text(path).splitlines()
    except Exception as e:
        print(f"[error reading log] {e}")
        return

    tail = data[-lines:] if lines > 0 else data
    for line in tail:
        print(line)


# Public aliases (IMPORTANT)
print_tail = _print_tail_impl
tail_file = _print_tail_impl


# ----------------------------
# Run status inference (log-driven)
# ----------------------------


def infer_run_status(path: Path) -> str:
    """
    Primary signal: RUN_STATUS=<value>
      completed | api_quota | oauth_quota | auth_invalid | failed

    Backward-compatible heuristics preserved.
    """
    try:
        text = read_text(path)
    except Exception:
        return "unknown"

    if "RUN_STATUS=completed" in text:
        return "completed"
    if "RUN_STATUS=api_quota" in text:
        return "api_quota"
    if "RUN_STATUS=oauth_quota" in text:
        return "oauth_quota"
    if "RUN_STATUS=auth_invalid" in text:
        return "auth_invalid"
    if "RUN_STATUS=failed" in text:
        return "failed"

    # Legacy fallback
    if "Done: OK" in text:
        return "completed"
    if "API key quota exhaustion" in text:
        return "api_quota"
    if "OAuth quota exhaustion" in text:
        return "oauth_quota"
    if "OAuth invalid" in text:
        return "auth_invalid"
    if "Done: failed" in text:
        return "failed"

    return "unknown"


# ----------------------------
# Run listing models
# ----------------------------


@dataclass(frozen=True)
class RunFile:
    run_id: str
    path: Path
    mtime: float
    size: int


def list_run_files(log_dir: Path) -> list[RunFile]:
    if not log_dir.exists():
        return []

    items: list[RunFile] = []
    for p in log_dir.glob("*.log"):
        try:
            st = p.stat()
        except OSError:
            continue
        items.append(
            RunFile(
                run_id=p.stem,
                path=p,
                mtime=st.st_mtime,
                size=st.st_size,
            )
        )

    items.sort(key=lambda r: r.mtime, reverse=True)
    return items


def format_mtime(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


# ----------------------------
# CLI output helpers
# ----------------------------


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    """
    Simple fixed-width table printer for CLI output.
    """
    if not rows:
        print("(no results)")
        return

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    fmt = "  ".join(f"{{:{w}}}" for w in widths)

    print(fmt.format(*headers))
    print(fmt.format(*("-" * w for w in widths)))

    for row in rows:
        print(fmt.format(*(str(c) for c in row)))
