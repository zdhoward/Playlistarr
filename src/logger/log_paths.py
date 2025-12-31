from __future__ import annotations

from pathlib import Path
from env import LOGS_DIR


def module_logs_dir(command: str) -> Path:
    return LOGS_DIR / command


def profile_logs_dir(command: str, profile: str) -> Path:
    return LOGS_DIR / command / profile
