from __future__ import annotations

import argparse
from pathlib import Path

from cli.common import (
    dispatch_subparser_help,
    find_log_file,
    print_tail,
    resolve_log_dir,
)


def build_logs_parser(subparsers: argparse._SubParsersAction) -> None:
    logs = subparsers.add_parser("logs", help="Log utilities")
    lsub = logs.add_subparsers(dest="logs_cmd", required=True)

    help_p = lsub.add_parser("help", help="Show help for logs")
    help_p.add_argument("path", nargs="*", help="Subcommand path (e.g. list, show)")
    help_p.set_defaults(action="help", _help_parser=logs)

    list_p = lsub.add_parser("list", help="List log files")
    list_p.add_argument("--profile", help="Profile name (logs/<profile>/)")
    list_p.add_argument("--dir", help="Explicit log directory")
    list_p.set_defaults(action="list")

    show_p = lsub.add_parser("show", help="Show a log file (tail)")
    show_p.add_argument("name", help="Log filename or stem")
    show_p.add_argument("--profile", help="Profile name (logs/<profile>/)")
    show_p.add_argument("--dir", help="Explicit log directory")
    show_p.add_argument("--tail", type=int, default=120, help="Lines from end")
    show_p.set_defaults(action="show")


def handle_logs(args: argparse.Namespace) -> int:
    if args.action == "help":
        return dispatch_subparser_help(
            args._help_parser, list(getattr(args, "path", []) or [])
        )

    log_dir = resolve_log_dir(
        profile=getattr(args, "profile", None), explicit=getattr(args, "dir", None)
    )

    if args.action == "list":
        if not log_dir.exists():
            print("No logs directory found")
            return 0
        for p in sorted(log_dir.glob("*.log")):
            print(p.name)
        return 0

    if args.action == "show":
        path = find_log_file(log_dir, args.name)
        if not path:
            print(f"Log not found: {args.name}")
            return 1
        print_tail(path, int(args.tail))
        return 0

    raise SystemExit(f"Unknown logs action: {args.action}")
