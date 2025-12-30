from pathlib import Path
import logging
from env import get_env

from rich.logging import RichHandler
from rich.console import Console

_INITIALIZED = False


def get_logger(name: str):
    return logging.getLogger(name)


def init_logging():
    global _INITIALIZED
    if _INITIALIZED:
        return

    env = get_env()

    log_dir = Path(env.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logfile = log_dir / "run.log"

    handlers = []

    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)

    # ============================================================
    # File logging (always full fidelity, plain text)
    # ============================================================

    file_handler = logging.FileHandler(logfile, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))
    handlers.append(file_handler)

    # ============================================================
    # Console logging (Rich, user-facing)
    # ============================================================

    # Console logging (Rich)
    if not env.quiet:
        console_level = logging.getLevelName(env.log_level)
        if not isinstance(console_level, int):
            console_level = logging.INFO

        # --verbose forces at least INFO
        if env.verbose and console_level > logging.INFO:
            console_level = logging.INFO

        console = RichHandler(
            level=console_level,
            rich_tracebacks=True,
            show_time=False,
            show_level=True,
            show_path=False,
            markup=True,
        )

        handlers.append(console)

    # ============================================================
    # Root logger
    # ============================================================

    root = logging.getLogger()
    root.setLevel(env.log_level)

    # Remove any previous handlers (critical for reloads, tests, pycharm, etc)
    for h in list(root.handlers):
        root.removeHandler(h)

    for h in handlers:
        root.addHandler(h)

    _INITIALIZED = True
