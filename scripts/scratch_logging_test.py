import logging
import os

from rich.logging import RichHandler

# Simulate runtime env state (what bootstrap_run_context would set)
os.environ["PLAYLISTARR_VERBOSE"] = "1"

# ---- logging init (must mirror logger.init_logging) ----

logging.root.handlers.clear()

level = logging.DEBUG if os.environ.get("PLAYLISTARR_VERBOSE") else logging.INFO
logging.root.setLevel(level)

handler = RichHandler(
    show_level=True,
    show_time=False,
    show_path=False,
)

# CRITICAL: formatter must NOT include level
handler.setFormatter(logging.Formatter("%(message)s"))

logging.root.addHandler(handler)

# ---- test logger ----

logger = logging.getLogger("test")

print("ROOT LEVEL:", logging.root.level)

logger.debug("DEBUG from scratch Rich test")
logger.info("INFO from scratch Rich test")
