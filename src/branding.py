PLAYLISTARR_BANNER = """

 _____ _         _ _     _
|  _  | |___ _ _| |_|___| |_ ___ ___ ___
|   __| | .'| | | | |_ -|  _| .'|  _|  _|
|__|  |_|__,|_  |_|_|___|_| |__,|_| |_|
            |___|


"""


def PLAYLISTARR_HEADER(title: str, pad=8, motif="•⊱✦⊰•", min_width=80):
    title = title.strip()

    # Natural content width
    content_width = len(title) + pad * 2

    # Enforce minimum width
    content_width = max(content_width, min_width)

    motif_width = len(motif)

    # How much space is available for filler after motif
    filler_space = content_width - motif_width

    # Split evenly
    left_width = filler_space // 2
    right_width = filler_space - left_width

    left_fill = "═" * left_width
    right_fill = "═" * right_width

    top = f"╔{left_fill}{motif}{right_fill}╗"
    bottom = f"╚{left_fill}{motif}{right_fill}╝"

    centered_title = title.center(content_width)
    middle = f"│{centered_title}│"

    return f"\n\n{top}\n{middle}\n{bottom}\n"


def make_footer(width):
    return f"╚{'═' * (width - 2)}╝"


PLAYLISTARR_SECTION_END = """

・‥…━━━━━━━•⊱✦⊰•━━━━━━━…‥・

"""

PLAYLISTARR_DIVIDER = """

⫘⫘⫘⫘⫘⫘⫘⫘⫘⫘⫘⫘⫘⫘⫘⫘

"""
