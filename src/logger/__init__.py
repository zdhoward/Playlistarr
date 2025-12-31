from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from env import get_logging_env
from .console import build_console_handler
from .file import build_file_handler
from .log_paths import module_logs_dir, profile_logs_dir
from .retention import enforce_retention

_INITIALIZED = False
_FILE_HANDLER: Optional[logging.FileHandler] = None


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def _level_to_int(level: str) -> int:
    try:
        return int(level)
    except Exception:
        return getattr(logging, level.upper(), logging.INFO)


def init_logging(
    module: str = "playlistarr",
    profile: Optional[str] = None,
) -> None:
    """
    Idempotent logging initialization.

    Contract:
    - Safe to call multiple times
    - Root handlers are exactly: console + optional file
    - Root level updates based on current env flags (verbose, log_level)
    """
    global _INITIALIZED, _FILE_HANDLER

    le = get_logging_env()
    root_level = logging.DEBUG if le.verbose else _level_to_int(le.log_level)

    root = logging.getLogger()
    root.setLevel(root_level)
    root.propagate = False

    # Always normalize handlers to avoid "half configured" states
    keep: list[logging.Handler] = []
    if _FILE_HANDLER is not None:
        keep.append(_FILE_HANDLER)

    root.handlers.clear()
    root.addHandler(build_console_handler())
    for h in keep:
        root.addHandler(h)

    _INITIALIZED = True

    # Optional file logging (never crash app if this fails)
    try:
        log_dir: Path = (
            profile_logs_dir(module, profile) if profile else module_logs_dir(module)
        )

        enforce_retention(log_dir, int(le.log_retention))

        logfile = log_dir / "run.log"

        if _FILE_HANDLER is None:
            _FILE_HANDLER = build_file_handler(logfile)
            root.addHandler(_FILE_HANDLER)

    except Exception:
        pass


# Ensure subprocesses/stage scripts get a console handler even if they never call init_logging().
# This is safe because init_logging() is idempotent and will be re-called later by playlistarr/cli_sync.
try:
    init_logging()
except Exception:
    # absolutely never block imports
    pass
