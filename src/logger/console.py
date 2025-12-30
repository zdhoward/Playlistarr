from __future__ import annotations

import logging

from rich.logging import RichHandler


_MESSAGE_COLUMN = 12


class BracketedLevelFilter(logging.Filter):
    LEVEL_STYLES = {
        "DEBUG": "dim",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold red",
    }

    def filter(self, record: logging.LogRecord) -> bool:
        level = f"[ {record.levelname} ]"
        style = self.LEVEL_STYLES.get(record.levelname, "")
        if style:
            level = f"[{style}]{level}[/{style}]"

        padding = max(1, _MESSAGE_COLUMN - len(record.levelname) - 4)
        record.msg = f"{level}{' ' * padding}{record.getMessage()}"
        record.args = ()
        return True


def build_console_handler(level: int) -> logging.Handler:
    console = RichHandler(
        level=level,
        rich_tracebacks=True,
        show_time=False,
        show_level=False,
        show_path=False,
        markup=True,
    )
    console.addFilter(BracketedLevelFilter())
    return console
