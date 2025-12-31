from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

from env import get_logging_env
from .console import build_console_handler
from .file import build_file_handler, repoint_file_handler
from .log_paths import module_logs_dir, profile_logs_dir
from .retention import enforce_retention
from . import state as _state


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def _level_to_int(level: str | int) -> int:
    if isinstance(level, int):
        return level
    lvl = logging.getLevelName(str(level).upper())
    return lvl if isinstance(lvl, int) else logging.INFO


def _ensure_run_id() -> str:
    run_id = os.environ.get("PLAYLISTARR_RUN_ID")
    if not run_id:
        run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        os.environ["PLAYLISTARR_RUN_ID"] = run_id
    return run_id


def _target_paths() -> tuple[str, str | None, Path]:
    command = os.environ.get("PLAYLISTARR_COMMAND") or "bootstrap"
    profile = os.environ.get("PLAYLISTARR_PROFILE_NAME") or os.environ.get(
        "PLAYLISTARR_PROFILE"
    )

    log_dir = (
        profile_logs_dir(command, profile) if profile else module_logs_dir(command)
    )
    run_id = _ensure_run_id()
    logfile = log_dir / f"{command}-{run_id}.log"
    return command, profile, logfile


def _squelch_noisy_loggers() -> None:
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def init_logging() -> None:
    """
    Initialize logging for the entire process.

    - Handlers are attached ONLY to the root logger.
    - Named loggers inherit via propagation.
    - Safe to call multiple times; file handler is repointed, not stacked.
    """
    env = get_logging_env()
    _squelch_noisy_loggers()

    root = logging.getLogger()
    _, _, logfile = _target_paths()

    log_dir = logfile.parent
    log_dir.mkdir(parents=True, exist_ok=True)
    enforce_retention(log_dir, int(env.log_retention))

    # Base level from env, but verbose forces DEBUG everywhere.
    root_level = logging.DEBUG if env.verbose else _level_to_int(env.log_level)

    if _state.INITIALIZED and _state.LOG_FILE_PATH == logfile:
        root.setLevel(root_level)
        return

    existing_file: logging.FileHandler | None = None
    for h in list(root.handlers):
        if isinstance(h, logging.FileHandler):
            existing_file = h
            break

    root.handlers.clear()
    root.setLevel(root_level)

    if existing_file is not None:
        repoint_file_handler(existing_file, logfile)
        root.addHandler(existing_file)
    else:
        root.addHandler(build_file_handler(logfile))

    # Console handler (Rich) only when not quiet and not interactive UI mode
    if not env.quiet and not env.interactive:
        console_level = logging.DEBUG if env.verbose else root_level
        root.addHandler(build_console_handler(console_level))

    _state.INITIALIZED = True
    _state.RUN_ID = os.environ.get("PLAYLISTARR_RUN_ID")
    _state.LOG_DIR = log_dir
    _state.LOG_FILE_PATH = logfile
