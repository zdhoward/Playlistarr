from __future__ import annotations

from pathlib import Path
from env import LOGS_DIR


def module_logs_dir(command: str) -> Path:
    path = LOGS_DIR / command
    path.mkdir(parents=True, exist_ok=True)
    return path


def profile_logs_dir(command: str, profile: str) -> Path:
    path = LOGS_DIR / command / profile
    path.mkdir(parents=True, exist_ok=True)
    return path
