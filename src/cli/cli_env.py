from __future__ import annotations

import argparse

from env import get_env
from cli.render import RENDER
from cli.common import dispatch_subparser_help


def build_env_parser(subparsers: argparse._SubParsersAction) -> None:
    env = subparsers.add_parser("env", help="Environment utilities")
    sub = env.add_subparsers(dest="env_cmd", required=True)

    help_p = sub.add_parser("help", help="Show help for env")
    help_p.add_argument("path", nargs="*", help="Subcommand path")
    help_p.set_defaults(action="help", _help_parser=env)

    dump_p = sub.add_parser("dump", help="Show resolved runtime environment")
    dump_p.set_defaults(action="dump")


def handle_env(args: argparse.Namespace) -> int:
    if args.action == "help":
        return dispatch_subparser_help(
            args._help_parser, list(getattr(args, "path", []) or [])
        )

    if args.action == "dump":
        return handle_env_dump()

    raise RuntimeError(f"Unknown env action: {args.action}")


def handle_env_dump() -> int:
    env = get_env()
    data = env.as_dict()

    RENDER.print("\n[bold]Runtime Environment[/bold]")
    RENDER.print("─" * 50)

    for section, values in data.items():
        RENDER.print(f"\n[bold cyan]{section}[/bold cyan]")
        for key, value in values.items():
            RENDER.print(f"  {key:<20} = {value}")

    RENDER.print()
    return 0
