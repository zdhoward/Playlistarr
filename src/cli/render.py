from rich.console import Console
import sys

RENDER = Console(
    file=sys.stdout,
    force_terminal=True,
    soft_wrap=True,
)
