from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time


class RunStatus(str, Enum):
    OK = "ok"
    FAILED = "failed"
    API_QUOTA = "api_quota"
    OAUTH_QUOTA = "oauth_quota"
    AUTH_INVALID = "auth_invalid"
    RUNNING = "running"


class RunStage(str, Enum):
    INIT = "init"
    OAUTH_HEALTH = "oauth_health"
    DISCOVERY = "discovery"
    SYNC = "sync"
    INVALIDATION_PLAN = "invalidation_plan"
    INVALIDATION_APPLY = "invalidation_apply"
    DONE = "done"


@dataclass
class RunProgress:
    current: int = 0
    total: int = 0

    def reset(self, total: int) -> None:
        self.current = 0
        self.total = total

    def advance(self, step: int = 1) -> None:
        self.current += step


@dataclass
class RunCounts:
    artists_processed: int = 0
    new_items: int = 0
    existing_items: int = 0
    removed_items: int = 0


@dataclass
class QuotaState:
    api_key_index: int = 0
    api_key_count: int = 0
    oauth_exhausted: bool = False


@dataclass
class RunMetadata:
    run_id: str
    command: str
    profile: Optional[str]
    playlist_id: Optional[str]
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None


@dataclass
class RunState:
    """
    Canonical runtime state for a Playlistarr execution.

    This object is mutated by the runner only.
    UI, CLI, logging, and summaries must treat it as read-only.
    """

    metadata: RunMetadata
    status: RunStatus = RunStatus.RUNNING
    stage: RunStage = RunStage.INIT

    progress: RunProgress = field(default_factory=RunProgress)
    counts: RunCounts = field(default_factory=RunCounts)
    quota: QuotaState = field(default_factory=QuotaState)

    stop_reason: Optional[str] = None

    # ------------------------------------------------------------------
    # Stage management
    # ------------------------------------------------------------------

    def set_stage(self, stage: RunStage) -> None:
        self.stage = stage

    # ------------------------------------------------------------------
    # Progress reporting
    # ------------------------------------------------------------------

    def start_progress(self, total: int) -> None:
        self.progress.reset(total)

    def advance_progress(self, step: int = 1) -> None:
        self.progress.advance(step)

    # ------------------------------------------------------------------
    # Counters
    # ------------------------------------------------------------------

    def mark_artist_processed(self) -> None:
        self.counts.artists_processed += 1

    def add_new_item(self, count: int = 1) -> None:
        self.counts.new_items += count

    def add_existing_item(self, count: int = 1) -> None:
        self.counts.existing_items += count

    def add_removed_item(self, count: int = 1) -> None:
        self.counts.removed_items += count

    # ------------------------------------------------------------------
    # Quota handling
    # ------------------------------------------------------------------

    def set_api_key_rotation(self, index: int, total: int) -> None:
        self.quota.api_key_index = index
        self.quota.api_key_count = total

    def mark_oauth_exhausted(self) -> None:
        self.quota.oauth_exhausted = True
        self.status = RunStatus.OAUTH_QUOTA
        self.stop_reason = "oauth_quota"

    def mark_api_quota_exhausted(self) -> None:
        self.status = RunStatus.API_QUOTA
        self.stop_reason = "api_quota"

    # ------------------------------------------------------------------
    # Completion
    # ------------------------------------------------------------------

    def finish_ok(self) -> None:
        self.status = RunStatus.OK
        self.stage = RunStage.DONE
        self.metadata.finished_at = time.time()

    def finish_failed(self, reason: str) -> None:
        self.status = RunStatus.FAILED
        self.stop_reason = reason
        self.stage = RunStage.DONE
        self.metadata.finished_at = time.time()

    # ------------------------------------------------------------------
    # Derived helpers (read-only)
    # ------------------------------------------------------------------

    @property
    def runtime_seconds(self) -> float:
        end = self.metadata.finished_at or time.time()
        return round(end - self.metadata.started_at, 2)
