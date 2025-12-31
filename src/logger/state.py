from __future__ import annotations

from pathlib import Path
from typing import Optional

INITIALIZED: bool = False
RUN_ID: Optional[str] = None
LOG_DIR: Optional[Path] = None
LOG_FILE_PATH: Optional[Path] = None
