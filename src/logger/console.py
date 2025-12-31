from __future__ import annotations

import logging
import sys
from dataclasses import dataclass

from rich.console import Console
from rich.logging import RichHandler

from env import get_logging_env

# Console used by RichHandler (stdout so subprocess-forwarding works)
UI_CONSOLE = Console(
    file=sys.stdout,
    force_terminal=True,
    soft_wrap=True,
)


@dataclass(frozen=True)
class ConsoleGateFilter(logging.Filter):
    """
    Gate console output when interactive UI mode is enabled.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        le = get_logging_env()

        if le.quiet:
            return False

        # In interactive mode, only allow logs explicitly marked as passthrough
        if le.interactive and not getattr(record, "passthrough", False):
            return False

        return True


def build_console_handler() -> logging.Handler:
    handler = RichHandler(
        console=UI_CONSOLE,
        show_level=True,
        show_time=False,
        show_path=False,
        markup=True,
    )

    # IMPORTANT:
    # - RichHandler renders the level column.
    # - Formatter must NOT include %(levelname)s or you get duplicates.
    # - Also don't prepend your own "|" — RichHandler already handles layout.
    handler.setFormatter(logging.Formatter("%(message)s"))

    handler.addFilter(ConsoleGateFilter())
    return handler


def log_passthrough(level: int, msg: str) -> None:
    logging.getLogger().log(level, msg, extra={"passthrough": True})
