from __future__ import annotations

import logging
from pathlib import Path


def build_file_handler(logfile: Path) -> logging.FileHandler:
    """
    Create a FileHandler and eagerly create the log file.

    This avoids Windows buffering issues where the file does not
    exist on disk until the first flush.
    """
    logfile.parent.mkdir(parents=True, exist_ok=True)

    # Touch file eagerly so it exists immediately
    try:
        logfile.touch(exist_ok=True)
    except Exception:
        pass

    handler = logging.FileHandler(logfile, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | [%(levelname)s] | %(name)s | %(message)s")
    )
    return handler


def repoint_file_handler(new_logfile: Path) -> None:
    root = logging.getLogger()

    # Ensure target exists before repoint
    try:
        new_logfile.parent.mkdir(parents=True, exist_ok=True)
        new_logfile.touch(exist_ok=True)
    except Exception:
        pass

    for handler in root.handlers:
        if isinstance(handler, logging.FileHandler):
            handler.acquire()
            try:
                handler.close()
                handler.baseFilename = str(new_logfile)
                handler.stream = handler._open()
            finally:
                handler.release()
