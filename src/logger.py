from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from env import get_env
from rich.logging import RichHandler
from paths import LOGS_DIR, module_logs_dir, profile_logs_dir


# ---------------------------------------------------------------------
# State
# ---------------------------------------------------------------------

_INITIALIZED = False
_LOG_FILE_PATH: Optional[Path] = None
_LOG_DIR: Optional[Path] = None

_MESSAGE_COLUMN = 12


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
    global _INITIALIZED, _LOG_FILE_PATH, _LOG_DIR

    env = get_env()

    # -----------------------------------------------------------------
    # Run ID
    # -----------------------------------------------------------------

    run_id = os.environ.get("PLAYLISTARR_RUN_ID")
    if not run_id:
        run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        os.environ["PLAYLISTARR_RUN_ID"] = run_id

    # -----------------------------------------------------------------
    # Context
    # -----------------------------------------------------------------

    command = os.environ.get("PLAYLISTARR_COMMAND") or "bootstrap"
    profile = (
        os.environ.get("PLAYLISTARR_PROFILE")
        or os.environ.get("PLAYLISTARR_PROFILE_NAME")
    )

    # -----------------------------------------------------------------
    # Target log directory
    # -----------------------------------------------------------------

    if profile:
        target_log_dir = profile_logs_dir(command, profile)
    else:
        target_log_dir = module_logs_dir(command)

    filename = f"{command}-{run_id}.log"
    target_log_file = target_log_dir / filename

    # -----------------------------------------------------------------
    # Upgrade path
    # -----------------------------------------------------------------

    if _INITIALIZED:
        if _LOG_DIR == target_log_dir:
            return

        _repoint_file_handler(target_log_file)
        _LOG_DIR = target_log_dir
        _LOG_FILE_PATH = target_log_file
        _enforce_retention(target_log_dir, int(env.log_retention))
        return

    # -----------------------------------------------------------------
    # First-time init
    # -----------------------------------------------------------------

    _LOG_DIR = target_log_dir
    _LOG_FILE_PATH = target_log_file

    _enforce_retention(target_log_dir, int(env.log_retention))

    handlers: list[logging.Handler] = []

    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)

    # ------------------------------------------------------------
    # File handler
    # ------------------------------------------------------------

    file_handler = logging.FileHandler(target_log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | [%(levelname)s] | %(name)s | %(message)s"
        )
    )
    handlers.append(file_handler)

    # ------------------------------------------------------------
    # Console handler
    # ------------------------------------------------------------

    if not env.quiet and not env.interactive:
        console_level = logging.getLevelName(env.log_level)
        if not isinstance(console_level, int):
            console_level = logging.INFO

        if env.verbose and console_level > logging.INFO:
            console_level = logging.INFO

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

        console = RichHandler(
            level=console_level,
            rich_tracebacks=True,
            show_time=False,
            show_level=False,
            show_path=False,
            markup=True,
        )
        console.addFilter(BracketedLevelFilter())
        handlers.append(console)

    root = logging.getLogger()
    root.setLevel(env.log_level)

    for h in list(root.handlers):
        root.removeHandler(h)

    for h in handlers:
        root.addHandler(h)

    _INITIALIZED = True


# ---------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------

def _repoint_file_handler(new_logfile: Path) -> None:
    root = logging.getLogger()
    for handler in root.handlers:
        if isinstance(handler, logging.FileHandler):
            handler.acquire()
            try:
                handler.close()
                handler.baseFilename = str(new_logfile)
                handler.stream = handler._open()
            finally:
                handler.release()


def _enforce_retention(log_dir: Path, keep: int) -> None:
    if keep <= 0:
        return

    logs = sorted(
        log_dir.glob("*.log"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    for old in logs[keep:]:
        try:
            old.unlink()
        except Exception:
            pass
