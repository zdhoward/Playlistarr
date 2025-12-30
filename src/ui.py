from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Optional

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.progress import BarColumn, Progress, TaskID, TextColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


_DOTS = ("", ".", "..", "...")


# ============================================================================
# State Models
# ============================================================================

@dataclass
class UIState:
    # Stage-level
    stage: str = ""
    stage_index: int = 0
    stage_total: int = 0

    # Per-item
    artist: str = ""
    task: str = ""
    old: int = 0
    new: int = 0

    # Discovery-only (optional)
    api_key_index: int = 0
    api_key_total: int = 0

    # Progress bar
    progress_label: str = ""
    progress_total: int = 0
    progress_completed: int = 0

    # Scrolling regions
    history: Deque[str] = field(default_factory=lambda: deque(maxlen=200))
    details: Deque[Text] = field(default_factory=lambda: deque(maxlen=200))


@dataclass
class UISummary:
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    stages: dict[str, str] = field(default_factory=dict)
    artists_processed: int = 0
    new_items: int = 0
    old_items: int = 0
    removed_items: int = 0

    stop_reason: str = "completed"  # completed | api_quota | oauth_quota | error


# ============================================================================
# Interactive UI
# ============================================================================

class InteractiveUI:
    """
    Runner-owned interactive console UI.

    Layout:
    - Top: scrolling history / details
    - Middle: pinned info line
    - Bottom: pinned progress bar

    Lifecycle:
    - start()  -> enter Rich Live mode
    - render() -> update UI state
    - stop()   -> exit Live mode
    - print_summary() -> print post-run summary (non-logged)
    """

    def __init__(self, *, refresh_per_second: int = 8, history_max: int = 200):
        self.console = Console()
        self.refresh_per_second = refresh_per_second

        self.state = UIState(
            history=deque(maxlen=history_max),
            details=deque(maxlen=history_max),
        )
        self.summary = UISummary()

        self._layout = self._build_layout()
        self._progress = self._build_progress()
        self._task_id: Optional[TaskID] = None

        self._live: Optional[Live] = None
        self._tick = 0
        self._last_render = 0.0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._live is not None:
            return

        self.summary.start_time = time.time()

        self._live = Live(
            self._layout,
            console=self.console,
            refresh_per_second=self.refresh_per_second,
            screen=True,
        )
        self._live.__enter__()

    def stop(self) -> None:
        if self._live is None:
            return

        try:
            self._live.__exit__(None, None, None)
        finally:
            self._live = None
            self.summary.end_time = time.time()

    # ------------------------------------------------------------------
    # Public API — state updates
    # ------------------------------------------------------------------

    def push_history(self, line: str) -> None:
        self.state.history.append(line)
        self.summary.artists_processed += 1

    def push_detail(self, line: str, *, style: str = "dim") -> None:
        self.state.details.append(Text(line, style=style))

    def set_stage(self, stage: str, *, index: int = 0, total: int = 0) -> None:
        self.state.stage = stage
        self.state.stage_index = index
        self.state.stage_total = total

        if stage:
            self.summary.stages.setdefault(stage, "running")
            self._ensure_progress_task(stage, total if total > 0 else None)

    def mark_stage(self, stage: str, result: str) -> None:
        self.summary.stages[stage] = result

    def set_artist(self, artist: str) -> None:
        self.state.artist = artist

    def set_task(self, task: str) -> None:
        self.state.task = task

    def set_counts(self, *, old: int | None = None, new: int | None = None) -> None:
        if old is not None:
            self.state.old = int(old)
            self.summary.old_items = self.state.old
        if new is not None:
            self.state.new = int(new)
            self.summary.new_items = self.state.new

    def set_removed(self, removed: int) -> None:
        self.summary.removed_items = int(removed)

    def set_api_key(self, *, index: int | None = None, total: int | None = None) -> None:
        if index is not None:
            self.state.api_key_index = int(index)
        if total is not None:
            self.state.api_key_total = int(total)

    def set_progress(
        self,
        *,
        completed: int | None = None,
        total: int | None = None,
        label: str | None = None,
    ) -> None:
        if label is not None:
            self.state.progress_label = label

        if total is not None:
            self.state.progress_total = int(total)
            self._ensure_progress_task(
                self.state.progress_label or self.state.stage or "Progress",
                self.state.progress_total,
            )

        if completed is not None:
            self.state.progress_completed = int(completed)
            if self._task_id is not None:
                self._progress.update(self._task_id, completed=self.state.progress_completed)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self, *, force: bool = False) -> None:
        now = time.time()
        if not force and (now - self._last_render) < (1.0 / max(1, self.refresh_per_second)):
            return

        self._last_render = now

        self._layout["history"].update(self._render_history())
        self._layout["info"].update(self._render_info())
        self._layout["progress"].update(self._progress)

        self._tick += 1
        if self._live is not None:
            self._live.refresh()

    # ------------------------------------------------------------------
    # Post-run Summary (UI only, not logged)
    # ------------------------------------------------------------------

    def print_summary(self) -> None:
        runtime = (self.summary.end_time or time.time()) - self.summary.start_time

        table = Table(show_header=False, box=None)
        table.add_row("Runtime", f"{runtime:.1f}s")
        table.add_row("Artists processed", str(self.summary.artists_processed))
        table.add_row("New items", str(self.summary.new_items))
        table.add_row("Existing items", str(self.summary.old_items))
        table.add_row("Removed items", str(self.summary.removed_items))
        table.add_row("Stop reason", self.summary.stop_reason)

        stages = Table(title="Stages", show_header=True, header_style="bold")
        stages.add_column("Stage")
        stages.add_column("Result")

        for stage, result in self.summary.stages.items():
            stages.add_row(stage, result)

        self.console.print()
        self.console.print(
            Panel.fit(
                table,
                title="Playlistarr Summary",
                border_style="cyan",
            )
        )
        self.console.print(stages)
        self.console.print()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="history", ratio=10),
            Layout(name="info", size=1),
            Layout(name="progress", size=3),
        )
        return layout

    def _build_progress(self) -> Progress:
        return Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=None),
            TextColumn("{task.percentage:>3.0f}%"),
            expand=True,
        )

    def _ensure_progress_task(self, label: str, total: int | None) -> None:
        if self._task_id is None:
            self._task_id = self._progress.add_task(label or "Progress", total=total or 100)
            return

        if label:
            self._progress.update(self._task_id, description=label)

        if total is not None and total > 0:
            self._progress.update(self._task_id, total=total)

    def _render_history(self) -> Group:
        items: list[Text] = []
        items.extend(list(self.state.details))
        items.extend(Text(h, style="white") for h in self.state.history)

        if not items:
            items.append(Text(""))

        return Group(*items)

    def _render_info(self) -> Text:
        dots = _DOTS[self._tick % len(_DOTS)]
        t = Text()

        stage = self.state.stage or "Stage"
        if self.state.stage_total:
            t.append(
                f"{stage} ({self.state.stage_index}/{self.state.stage_total})",
                style="bold cyan",
            )
        else:
            t.append(stage, style="bold cyan")

        t.append(" | ", style="dim")
        t.append(f"old: {self.state.old} | new: {self.state.new}", style="dim")

        if self.state.api_key_total:
            t.append(" | ", style="dim")
            t.append(
                f"API KEY ({self.state.api_key_index}/{self.state.api_key_total})",
                style="yellow",
            )

        if self.state.artist:
            t.append(" | ", style="dim")
            t.append(f"Artist: {self.state.artist}", style="green")

        if self.state.task:
            t.append(" | ", style="dim")
            t.append(f"Task: {self.state.task}{dots}", style="magenta")

        return t
