from __future__ import annotations

import logging
from pathlib import Path


def build_file_handler(logfile: Path) -> logging.FileHandler:
    logfile.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.FileHandler(logfile, encoding="utf-8")
    handler.setLevel(logging.NOTSET)

    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | [%(levelname)s] | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    return handler


def repoint_file_handler(handler: logging.FileHandler, new_logfile: Path) -> None:
    new_logfile.parent.mkdir(parents=True, exist_ok=True)

    handler.acquire()
    try:
        handler.close()
        handler.baseFilename = str(new_logfile)
        handler.stream = handler._open()
    finally:
        handler.release()
