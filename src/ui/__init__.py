from __future__ import annotations

import time
from collections import deque
from typing import Optional, Deque

from rich import box as rich_box
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TaskID
from rich.table import Table
from rich.text import Text

from ui.console import UI_CONSOLE
from ui.config import UIStyle
from ui.state import UIState, UISummary


_BOX_MAP = {
    "rounded": rich_box.ROUNDED,
    "square": rich_box.SQUARE,
    "heavy": rich_box.HEAVY,
    "ascii": rich_box.ASCII,
}


class InteractiveUI:
    def __init__(
        self, refresh_per_second: int = 10, style: UIStyle | None = None
    ) -> None:
        self.console = UI_CONSOLE
        self.refresh_per_second = refresh_per_second
        self.style = style or UIStyle()

        # These are used directly by runner.py
        self.state = UIState()
        self.summary = UISummary()

        self._recent_artists: Deque[str] = deque(maxlen=10)

        self._live: Optional[Live] = None

        self._progress = self._build_progress()
        self._progress_task: Optional[TaskID] = None

        self._layout = self._build_layout()

    # ─────────────────────────────
    # Lifecycle
    # ─────────────────────────────

    def start(self) -> None:
        if self._live is not None:
            return

        self.summary.start_time = time.time()

        # Ensure progress always renders immediately (even before any progress events)
        self._ensure_progress_task()

        self._live = Live(
            self._layout,
            console=self.console,
            refresh_per_second=self.refresh_per_second,
            screen=True,
        )
        self._live.__enter__()

        # Render first frame with whatever state runner set before/after start
        self.render()

    def stop(self) -> None:
        if self._live is None:
            return

        try:
            self._live.__exit__(None, None, None)
        finally:
            self._live = None
            self.summary.end_time = time.time()

    def render(self) -> None:
        # Rebuild panels from state every time so runner's direct mutations show up
        self._sync_recent_artists()

        self._layout["header"].update(self._render_header())
        self._layout["progress_block"].update(self._render_progress_block())
        self._layout["artists"].update(self._render_artists())
        self._layout["status"].update(self._render_status())

        if self._live is not None:
            self._live.refresh()

    def print_summary(self) -> None:
        from rich.table import Table
        from rich.panel import Panel
        from rich.text import Text
        from datetime import timedelta

        # Guard
        if not self.summary.start_time:
            return

        end = self.summary.end_time or time.time()
        duration = timedelta(seconds=int(end - self.summary.start_time))

        # Determine run status
        if self.summary.stop_reason:
            status = ("STOPPED", "yellow")
        elif any(v != "ok" for v in self.summary.stages.values()):
            status = ("ERROR", "red")
        else:
            status = ("SUCCESS", "green")

        header = Text.assemble(
            ("Playlistarr Run Summary\n", "bold"),
            ("Status: ", "dim"),
            (status[0], f"bold {status[1]}"),
            ("\nDuration: ", "dim"),
            (str(duration), "bold"),
        )

        # ── Stage table ──────────────────────
        stage_table = Table(
            show_header=True,
            header_style="bold",
            box=None,
            expand=True,
        )
        stage_table.add_column("#", justify="right", width=3)
        stage_table.add_column("Stage")
        stage_table.add_column("Result", justify="center")

        for i, (stage, result) in enumerate(self.summary.stages.items(), start=1):
            style = (
                "green"
                if result == "ok"
                else "yellow" if result == "skipped" else "red"
            )
            stage_table.add_row(str(i), stage, f"[{style}]{result}[/{style}]")

        # ── Totals / counts ──────────────────
        totals = Table.grid(padding=(0, 1))
        totals.add_column(justify="right", style="dim")
        totals.add_column(justify="left")

        if self.state.progress_total:
            totals.add_row(
                "Processed:",
                f"{self.state.progress_completed} / {self.state.progress_total}",
            )

        if self.state.old_count is not None:
            totals.add_row("Old items:", str(self.state.old_count))
        if self.state.new_count is not None:
            totals.add_row("New items:", str(self.state.new_count))

        if (
            self.state.api_key_index is not None
            and self.state.api_key_total is not None
        ):
            totals.add_row(
                "API keys used:",
                f"{self.state.api_key_index} / {self.state.api_key_total}",
            )

        if self.summary.stop_reason:
            totals.add_row("Stop reason:", f"[yellow]{self.summary.stop_reason}[/]")

        # ── Final layout ─────────────────────
        layout = Table.grid(expand=True)
        layout.add_row(stage_table)
        layout.add_row("")
        layout.add_row(totals)

        self.console.print(
            Panel(
                layout,
                title="Run Summary",
                subtitle=f"{status[0]}",
                border_style=status[1],
            )
        )

    # ─────────────────────────────
    # Event application
    # ─────────────────────────────

    def apply_event(self, evt: dict) -> None:
        event = evt.get("event")

        if event == "artist":
            self.state.artist = (evt.get("artist") or "").strip()
            self.state.progress_completed = (
                evt.get("completed", self.state.progress_completed)
                or self.state.progress_completed
            )

        elif event == "task":
            self.state.task = (evt.get("task") or "").strip()

        elif event == "counts":
            self.state.old_count = evt.get("old")
            self.state.new_count = evt.get("new")

        elif event == "api_key":
            self.state.api_key_index = evt.get("index")
            self.state.api_key_total = evt.get("total")

        elif event == "progress":
            completed = evt.get("completed")
            total = evt.get("total")
            label = evt.get("label")

            if isinstance(total, int) and total >= 0:
                self.state.progress_total = total
            if isinstance(completed, int) and completed >= 0:
                self.state.progress_completed = completed
            if isinstance(label, str) and label.strip():
                self.state.task = label.strip()

        # Ensure progress task exists and reflects current totals
        self._ensure_progress_task()

    # ─────────────────────────────
    # Layout / rendering
    # ─────────────────────────────

    def _build_layout(self) -> Layout:
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="progress_block", size=5),
            Layout(name="body"),
        )

        layout["body"].split_row(
            Layout(name="artists"),
            Layout(name="status", size=32),
        )

        # Initial placeholders
        layout["header"].update(self._render_header())
        layout["progress_block"].update(self._render_progress_block())
        layout["artists"].update(self._render_artists())
        layout["status"].update(self._render_status())

        return layout

    def _render_header(self) -> Panel:
        stage = self.state.stage or "—"
        idx = self.state.stage_index or 0
        total = self.state.stage_total or 0

        right = f"Stage {idx}/{total}: {stage}" if total else f"Stage: {stage}"
        text = Text.assemble(
            (self.style.header_title, "bold cyan"),
            (" — ", "dim"),
            (right, "bold"),
        )

        return self._panel(text, title="")

    def _render_progress_block(self) -> Panel:
        self._ensure_progress_task()

        artist = self.state.artist or "—"
        task = self.state.task or "—"

        line = Text.assemble(
            ("Task: ", "dim"),
            (task, "bold"),
            ("    ", ""),
            ("Artist: ", "dim"),
            (artist, "bold"),
        )

        table = Table.grid(padding=(0, 1))
        table.add_row(line)
        table.add_row(self._progress)

        return self._panel(table, title="Progress")

    def _render_artists(self) -> Panel:
        if not self._recent_artists:
            content = Text("—", style="dim")
            return self._panel(content, title="Recent Artists")

        t = Table.grid(padding=(0, 1))
        for a in self._recent_artists:
            t.add_row(Text(f"• {a}"))

        return self._panel(t, title="Recent Artists")

    def _render_status(self) -> Panel:
        t = Table.grid(padding=(0, 1))
        t.add_column(justify="right", style="dim")
        t.add_column(justify="left")

        if self.state.old_count is not None:
            t.add_row("Old:", str(self.state.old_count))
        else:
            t.add_row("Old:", "—")

        if self.state.new_count is not None:
            t.add_row("New:", str(self.state.new_count))
        else:
            t.add_row("New:", "—")

        if (
            self.state.api_key_index is not None
            and self.state.api_key_total is not None
        ):
            t.add_row(
                "API Key:", f"{self.state.api_key_index}/{self.state.api_key_total}"
            )
        else:
            t.add_row("API Key:", "—")

        if self.state.progress_total:
            t.add_row("Total:", str(self.state.progress_total))
            t.add_row("Done:", str(self.state.progress_completed))

        return self._panel(t, title="Status", dim_border=True)

    # ─────────────────────────────
    # Progress helpers
    # ─────────────────────────────

    def _build_progress(self) -> Progress:
        # Percentage centered (column centered)
        return Progress(
            BarColumn(
                bar_width=None,
                complete_style=self.style.progress_complete_color,
                finished_style=self.style.progress_finished_color,
            ),
            TextColumn(
                "[progress.percentage]{task.percentage:>3.0f}%[/]",
                justify="center",
            ),
            expand=True,
            console=self.console,
        )

    def _ensure_progress_task(self) -> None:
        if self._progress_task is None:
            self._progress_task = self._progress.add_task(
                self.style.progress_initial_label,
                total=(
                    max(self.state.progress_total, 1)
                    if self.state.progress_total
                    else 100
                ),
                completed=min(max(self.state.progress_completed, 0), 100),
            )

        total = (
            max(self.state.progress_total, 1)
            if self.state.progress_total
            else self._progress.tasks[0].total
        )
        completed = max(self.state.progress_completed, 0)

        # Keep total/completed in sync with state
        self._progress.update(self._progress_task, total=total, completed=completed)

    def _sync_recent_artists(self) -> None:
        a = (self.state.artist or "").strip()
        if not a:
            return
        if self._recent_artists and self._recent_artists[0] == a:
            return
        self._recent_artists.appendleft(a)

    # ─────────────────────────────
    # Panel helper
    # ─────────────────────────────

    def _panel(self, content, title: str, dim_border: bool = False) -> Panel:
        box_style = _BOX_MAP.get(self.style.panel_box.lower(), rich_box.ROUNDED)
        border = "dim" if dim_border else self.style.panel_border_color

        return Panel(
            content,
            title=title,
            box=box_style,
            border_style=border,
        )
