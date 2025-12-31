from rich.console import Console
import sys

# Dedicated console for Rich Live UI (stdout).
# MUST NOT be shared with logging.
UI_CONSOLE = Console(
    file=sys.stdout,
    force_terminal=True,
    soft_wrap=True,
)
