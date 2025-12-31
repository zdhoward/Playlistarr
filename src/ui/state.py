from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UIState:
    # Stage context
    stage: str = ""
    stage_index: int = 0
    stage_total: int = 0

    # Current activity
    artist: str = ""
    task: str = ""

    # Progress
    progress_completed: int = 0
    progress_total: int = 0

    # Counts/status
    old_count: Optional[int] = None
    new_count: Optional[int] = None

    # API key rotation
    api_key_index: Optional[int] = None
    api_key_total: Optional[int] = None


@dataclass
class UISummary:
    stages: dict[str, str] = field(default_factory=dict)  # stage name -> state.value
    stop_reason: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
