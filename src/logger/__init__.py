from __future__ import annotations

import logging

from env import get_env
from . import state
from .context import resolve_run_id, resolve_command, resolve_profile
from .log_paths import resolve_log_target
from .retention import enforce_retention
from .file import build_file_handler, repoint_file_handler
from .console import build_console_handler


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def init_logging() -> None:
    """
    Initialize logging for the entire process.

    Safe to call multiple times.
    """
    env = get_env()

    run_id = resolve_run_id()
    command = resolve_command()
    profile = resolve_profile()

    log_dir, logfile = resolve_log_target(command, run_id, profile)

    root = logging.getLogger()

    # -----------------------------------------------------------------
    # Upgrade / repoint path
    # -----------------------------------------------------------------

    if state.INITIALIZED:
        if state.LOG_DIR == log_dir:
            return

        repoint_file_handler(logfile)

        # Defensive invariant: exactly one FileHandler must exist
        file_handlers = [
            h for h in root.handlers if isinstance(h, logging.FileHandler)
        ]
        if len(file_handlers) != 1:
            raise RuntimeError(
                "Logger invariant violated: expected exactly one FileHandler"
            )

        state.LOG_DIR = log_dir
        state.LOG_FILE_PATH = logfile
        enforce_retention(log_dir, int(env.log_retention))
        return

    # -----------------------------------------------------------------
    # First-time initialization
    # -----------------------------------------------------------------

    state.LOG_DIR = log_dir
    state.LOG_FILE_PATH = logfile
    enforce_retention(log_dir, int(env.log_retention))

    handlers: list[logging.Handler] = []

    # Silence noisy libraries
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)

    # File handler (authoritative)
    handlers.append(build_file_handler(logfile))

    # Console handler (optional)
    if not env.quiet and not env.interactive:
        console_level = logging.getLevelName(env.log_level)
        if not isinstance(console_level, int):
            console_level = logging.INFO

        if env.verbose and console_level > logging.INFO:
            console_level = logging.INFO

        handlers.append(build_console_handler(console_level))

    root.setLevel(env.log_level)

    for h in list(root.handlers):
        root.removeHandler(h)

    for h in handlers:
        root.addHandler(h)

    state.INITIALIZED = True
