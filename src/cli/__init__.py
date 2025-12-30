"""
Playlistarr CLI package.

This package contains argparse-based subcommands.

Each module exposes:
- build_*_parser(subparsers)
- handle_*(args) -> int

No side effects or imports should occur at package import time.
"""
from __future__ import annotations

__all__ = [
    "cli_sync",
    "cli_profiles",
    "cli_runs",
    "cli_logs",
    "cli_auth",
]
