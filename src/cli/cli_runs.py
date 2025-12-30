from __future__ import annotations

import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

from cli.common import (
    iter_log_files,
    resolve_log_dir,
    print_table,
    tail_file,
)


# ============================================================================
# Run status inference
# ============================================================================


def infer_run_status(log_path: Path) -> str:
    """
    Infer run status from log file.

    Priority:
      1. Explicit RUN_STATUS=... line (authoritative)
      2. Legacy heuristics
      3. unknown
    """
    try:
        for line in log_path.read_text(errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("RUN_STATUS="):
                return line.split("=", 1)[1].strip()
    except Exception:
        return "unknown"

    # Legacy fallbacks (older logs)
    try:
        text = log_path.read_text(errors="ignore")
        if "Done: OK" in text:
            return "completed"
        if "OAuth quota exhausted" in text:
            return "oauth_quota"
        if "quota exhausted" in text.lower():
            return "api_quota"
        if "Done: failed" in text:
            return "failed"
    except Exception:
        pass

    return "unknown"


# ============================================================================
# CLI wiring
# ============================================================================


def build_runs_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("runs", help="Inspect past runs (log-driven)")
    sp = p.add_subparsers(dest="runs_cmd", required=True)

    sp.add_parser("help", help="Show help for runs")

    list_p = sp.add_parser("list", help="List runs")
    list_p.add_argument("--profile", help="Profile name (logs/<profile>/)")
    list_p.add_argument("--dir", help="Explicit log directory")

    latest_p = sp.add_parser("latest", help="Show latest run")
    latest_p.add_argument("--profile", help="Profile name (logs/<profile>/)")
    latest_p.add_argument("--dir", help="Explicit log directory")

    show_p = sp.add_parser("show", help="Show a specific run")
    show_p.add_argument("run_id", help="Run id (timestamp) or filename stem")
    show_p.add_argument("--profile", help="Profile name (logs/<profile>/)")
    show_p.add_argument("--dir", help="Explicit log directory")
    show_p.add_argument("--tail", type=int, default=40, help="Lines to show from end")


def handle_runs(args: argparse.Namespace) -> int:
    log_dir = resolve_log_dir(profile=args.profile, explicit=args.dir)

    if args.runs_cmd == "help":
        print("Use: playlistarr runs [list|latest|show]")
        return 0

    logs = sorted(iter_log_files(log_dir), reverse=True)

    if args.runs_cmd == "list":
        rows = []
        for p in logs:
            stat = infer_run_status(p)
            ts = datetime.fromtimestamp(p.stat().st_mtime)
            rows.append(
                [
                    p.stem,
                    stat,
                    ts.strftime("%Y-%m-%d %H:%M:%S"),
                    f"{p.stat().st_size} bytes",
                ]
            )
        print_table(["run_id", "state", "time", "size"], rows)
        return 0

    if args.runs_cmd == "latest":
        if not logs:
            print("No runs found")
            return 1

        p = logs[0]
        stat = infer_run_status(p)
        ts = datetime.fromtimestamp(p.stat().st_mtime)

        print(f"{p.stem}  {stat}  " f"{ts.strftime('%Y-%m-%d %H:%M:%S')}  {p}")
        return 0

    if args.runs_cmd == "show":
        name = args.run_id
        match: Optional[Path] = None

        for p in logs:
            if p.stem == name or p.name == name:
                match = p
                break

        if not match:
            print(f"Run not found: {name}")
            return 1

        stat = infer_run_status(match)
        ts = datetime.fromtimestamp(match.stat().st_mtime)

        print(f"Run:   {match.stem}")
        print(f"Path:  {match}")
        print(f"Time:  {ts.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Size:  {match.stat().st_size} bytes")
        print(f"State: {stat}")
        print()

        tail_file(match, args.tail)
        return 0

    return 1
