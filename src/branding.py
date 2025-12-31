from __future__ import annotations

import shutil
from typing import Iterable, Literal

# --------------------------------------------------
# Layout constants
# --------------------------------------------------

DEFAULT_WIDTH = 80
LOG_GUTTER_WIDTH = 10  # "[ INFO ]  " etc.

Width = int | Literal["auto"]


def _resolve_width(width: Width) -> int:
    if width == "auto":
        try:
            cols = shutil.get_terminal_size().columns
        except Exception:
            cols = DEFAULT_WIDTH
        return max(DEFAULT_WIDTH, cols - LOG_GUTTER_WIDTH)
    return max(DEFAULT_WIDTH, int(width))


# --------------------------------------------------
# Banner
# --------------------------------------------------

PLAYLISTARR_BANNER = """

 _____ _         _ _     _
|  _  | |___ _ _| |_|___| |_ ___ ___ ___
|   __| | .'| | | | |_ -|  _| .'|  _|  _|
|__|  |_|__,|_  |_|_|___|_| |__,|_| |_|
            |___|

"""


# --------------------------------------------------
# Headers / sections
# --------------------------------------------------


def PLAYLISTARR_HEADER(
    title: str,
    *,
    width: Width = DEFAULT_WIDTH,
    pad: int = 8,
    motif: str = "•⊱✦⊰•",
) -> str:
    title = title.strip()
    w = _resolve_width(width)
    inner = w - 2

    min_title = len(title) + pad * 2
    inner = max(inner, min_title)

    filler = inner - len(motif)
    left = filler // 2
    right = filler - left

    top = f"╔{'═' * left}{motif}{'═' * right}╗"
    mid = f"│{title.center(inner)}│"
    bot = f"╚{'═' * left}{motif}{'═' * right}╝"

    return f"\n{top}\n{mid}\n{bot}\n\n"


def PLAYLISTARR_DIVIDER(
    *,
    width: Width = DEFAULT_WIDTH,
    char: str = "⫘",
) -> str:
    w = _resolve_width(width)
    return f"\n{char * w}\n"


def PLAYLISTARR_SECTION_END(
    *,
    width: Width = DEFAULT_WIDTH,
    motif: str = "•⊱✦⊰•",
    fill: str = "━",
) -> str:
    w = _resolve_width(width)
    side = max(0, (w - len(motif)) // 2)
    line = f"{fill * side}{motif}{fill * (w - side - len(motif))}"
    return f"\n{line}\n"


# --------------------------------------------------
# Boxed blocks (highlight sections)
# --------------------------------------------------


def PLAYLISTARR_BOX(
    lines: Iterable[str],
    *,
    title: str | None = None,
    width: Width = DEFAULT_WIDTH,
) -> str:
    w = _resolve_width(width)
    inner = w - 2

    out: list[str] = []
    out.append(f"╔{'═' * inner}╗")

    if title:
        out.append(f"║{title.center(inner)}║")
        out.append(f"╟{'─' * inner}╢")

    for line in lines:
        out.append(f"║ {line.ljust(inner - 1)}║")

    out.append(f"╚{'═' * inner}╝")
    return "\n".join(out)


# --------------------------------------------------
# Symbols (JetBrains + Playlistarr)
# --------------------------------------------------


class SYMBOLS:
    # Status
    OK = "✔"
    FAIL = "✖"
    WARN = "⚠"
    INFO = "ℹ"

    # Flow
    RUNNING = "▶"
    DONE = "✓"
    SKIPPED = "⤼"
    BLOCKED = "⛔"
    RETRY = "↻"

    # Stages
    DISCOVERY = "🔍"
    INVALIDATE = "🚫"
    APPLY = "🧹"
    SYNC = "🔄"

    # Playlist ops
    ADD = "➕"
    REMOVE = "➖"
    KEEP = "✔"

    # Music
    MUSIC = "🎵"
    NOTE = "♪"
    ARTIST = "🎤"
    ALBUM = "💿"
    TRACK = "🎶"
    VIDEO = "🎬"
    PLAYLIST = "📻"

    # Infra
    API = "🔌"
    QUOTA = "📊"
    AUTH = "🔒"

    # Files
    FILE = "📄"
    FOLDER = "📁"
    CACHE = "🗄️"
    SAVE = "💾"
