from __future__ import annotations

from pathlib import Path
from typing import Tuple

from paths import module_logs_dir, profile_logs_dir


def resolve_log_target(
    command: str,
    run_id: str,
    profile: str | None,
) -> Tuple[Path, Path]:
    """
    Return (log_dir, log_file_path)
    """
    if profile:
        log_dir = profile_logs_dir(command, profile)
    else:
        log_dir = module_logs_dir(command)

    logfile = log_dir / f"{command}-{run_id}.log"
    return log_dir, logfile
