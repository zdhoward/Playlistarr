# src/logger/console.py
from __future__ import annotations

import logging
import sys
from rich.console import Console
from rich.logging import RichHandler

import os

from env import get_logging_env

UI_CONSOLE = Console(
    file=sys.stdout,
    force_terminal=True,
    soft_wrap=True,
)


class ConsoleGateFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        env = get_logging_env()

        # Only suppress console logging if quiet mode is explicitly requested
        if os.environ.get("PLAYLISTARR_UI") == "1":
            return False

        return True


def build_console_handler(level: int) -> logging.Handler:
    handler = RichHandler(
        console=Console(file=sys.stderr),
        show_time=False,
        show_level=True,
        show_path=False,
        markup=True,
    )
    handler.setFormatter(logging.Formatter("| %(message)s"))
    handler.addFilter(ConsoleGateFilter())
    return handler


def log_passthrough(level: int, msg: str) -> None:
    logging.getLogger().log(level, msg, extra={"passthrough": True})
