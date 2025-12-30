#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from env import PROJECT_ROOT

os.chdir(PROJECT_ROOT)


# ------------------------------------------------------------
# Minimal dotenv loader (silent, production-safe)
# ------------------------------------------------------------

def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()

        if " #" in v:
            v = v.split(" #", 1)[0].rstrip()
        elif "\t#" in v:
            v = v.split("\t#", 1)[0].rstrip()

        if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
            v = v[1:-1]

        if k and k not in os.environ:
            os.environ[k] = v


# ------------------------------------------------------------
# Help routing
# ------------------------------------------------------------

def _dispatch_help(parser: argparse.ArgumentParser, argv: list[str]) -> int:
    if not argv:
        parser.print_help()
        return 0

    if argv and argv[0] == "help":
        argv = argv[1:]

    for i in range(len(argv), 0, -1):
        try:
            tmp = build_parser()
            tmp.parse_args(argv[:i] + ["--help"])
            return 0
        except SystemExit:
            return 0

    parser.print_help()
    return 0


# ------------------------------------------------------------
# CLI construction
# ------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="playlistarr")
    sub = p.add_subparsers(dest="command", required=True)

    help_cmd = sub.add_parser("help", help="Show help")
    help_cmd.add_argument("path", nargs="*", help="Command path to show help for")
    help_cmd.set_defaults(_help=True)

    from cli.cli_sync import build_sync_parser
    from cli.cli_profiles import build_profiles_parser
    from cli.cli_runs import build_runs_parser
    from cli.cli_logs import build_logs_parser
    from cli.cli_auth import build_auth_parser

    build_sync_parser(sub)
    build_profiles_parser(sub)
    build_runs_parser(sub)
    build_logs_parser(sub)
    build_auth_parser(sub)

    return p


# ------------------------------------------------------------
# Main entrypoint
# ------------------------------------------------------------

def main() -> int:
    parser = build_parser()
    args, unknown = parser.parse_known_args()

    if getattr(args, "_help", False) or (unknown and unknown[-1] == "help"):
        return _dispatch_help(parser, sys.argv[1:])

    if args.command in ("sync", "run") and getattr(args, "profile", None) == "help":
        return _dispatch_help(parser, sys.argv[1:])

    # Fix run-id ONCE
    if "PLAYLISTARR_RUN_ID" not in os.environ:
        os.environ["PLAYLISTARR_RUN_ID"] = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # 🔑 THIS WAS MISSING — EXPORT COMMAND FOR LOGGER
    os.environ.setdefault("PLAYLISTARR_COMMAND", args.command)

    _load_dotenv(PROJECT_ROOT / ".env")

    if args.command in ("sync", "run"):
        from cli.cli_sync import handle_sync
        return handle_sync(args)

    if args.command == "profiles":
        from cli.cli_profiles import handle_profiles
        return handle_profiles(args)

    if args.command == "runs":
        from cli.cli_runs import handle_runs
        return handle_runs(args)

    if args.command == "logs":
        from cli.cli_logs import handle_logs
        return handle_logs(args)

    if args.command == "auth":
        from cli.cli_auth import handle_auth
        return handle_auth(args)

    raise RuntimeError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
