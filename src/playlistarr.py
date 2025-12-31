#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from bootstrap import bootstrap_base_env, bootstrap_run_context


def _dispatch_help(parser: argparse.ArgumentParser, argv: list[str]) -> int:
    # Support:
    #   playlistarr help
    #   playlistarr help sync
    #   playlistarr sync help
    if not argv:
        parser.print_help()
        return 0

    if argv and argv[0] == "help":
        argv = argv[1:]

    # Try progressively shorter prefixes until argparse accepts "--help"
    for i in range(len(argv), 0, -1):
        try:
            tmp = build_parser()
            tmp.parse_args(argv[:i] + ["--help"])
            return 0
        except SystemExit:
            return 0

    parser.print_help()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="playlistarr")

    sub = p.add_subparsers(dest="command", required=True)

    help_cmd = sub.add_parser("help", help="Show help")
    help_cmd.add_argument("path", nargs="*", help="Command path to show help for")
    help_cmd.set_defaults(_help=True)

    # Keep imports inside builder to avoid early side effects.
    from cli.cli_env import build_env_parser
    from cli.cli_sync import build_sync_parser
    from cli.cli_profiles import build_profiles_parser
    from cli.cli_runs import build_runs_parser
    from cli.cli_logs import build_logs_parser
    from cli.cli_auth import build_auth_parser

    build_env_parser(sub)
    build_sync_parser(sub)
    build_profiles_parser(sub)
    build_runs_parser(sub)
    build_logs_parser(sub)
    build_auth_parser(sub)

    return p


def main() -> int:
    # Load .env and base environment early
    bootstrap_base_env(config_dir="config", env_file=".env", required=False)

    # Resolve project root without importing env.py at import time
    project_root = Path(__file__).resolve().parent.parent
    os.chdir(project_root)

    parser = build_parser()
    args, unknown = parser.parse_known_args()

    # Unified help routing
    if getattr(args, "_help", False) or (unknown and unknown[-1] == "help"):
        return _dispatch_help(parser, sys.argv[1:])
    if args.command in ("sync",) and getattr(args, "profile", None) == "help":
        return _dispatch_help(parser, sys.argv[1:])

    # Stamp run context early (so subprocesses inherit it)
    bootstrap_run_context(
        command=args.command,
        profile_name=(
            getattr(args, "profile", None)
            if isinstance(getattr(args, "profile", None), str)
            else None
        ),
        profile_path=getattr(args, "profile_path", None),
        artists_csv=getattr(args, "csv", None) or getattr(args, "artists_csv", None),
        playlist_id=getattr(args, "playlist_id", None),
        verbose=bool(getattr(args, "verbose", False)),
        quiet=bool(getattr(args, "quiet", False)),
        interactive=bool(
            getattr(args, "ui", False) or getattr(args, "interactive", False)
        ),
    )

    # Initialize logging AFTER run-context env stamping
    from logger import init_logging, get_logger

    init_logging(
        module=args.command or "playlistarr",
        profile=getattr(args, "profile", None),
    )

    log = get_logger(__name__)
    log.info("Playlistarr starting")
    log.info(f"Command: {args.command}")

    # Dispatch
    if args.command == "env":
        from cli.cli_env import handle_env

        return handle_env(args)

    if args.command == "sync":
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
