from dataclasses import dataclass


@dataclass(frozen=True)
class UIStyle:
    # Human-friendly values (mapped in ui code)
    panel_box: str = "rounded"  # rounded, square, heavy, ascii
    panel_border_color: str = "cyan"

    # Progress styling
    progress_complete_color: str = "cyan"
    progress_finished_color: str = "green"

    # Initial labels
    header_title: str = "Playlistarr"
    progress_initial_label: str = "Starting…"
