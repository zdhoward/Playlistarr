from __future__ import annotations

from pathlib import Path


def enforce_retention(log_dir: Path, keep: int) -> None:
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
