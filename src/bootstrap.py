from __future__ import annotations

"""bootstrap.py

Process bootstrap for Playlistarr.

This module is intentionally tiny and side-effectful.

Rules:
1) Only bootstrap is allowed to *mutate* os.environ for shared run context.
2) Call bootstrap_base_env() exactly once at the true entrypoint.
3) Call bootstrap_run_context() after argparse parsing, before init_logging().

Everything else should treat environment variables as the source of truth.
"""

import os
from datetime import datetime
from pathlib import Path

from env import PROJECT_ROOT, _load_dotenv, reset_env_caches


_BOOTSTRAPPED = False


def bootstrap_base_env() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    dotenv_path = PROJECT_ROOT / "config" / ".env"

    if not dotenv_path.exists():
        raise RuntimeError(
            f"Missing required env file: {dotenv_path}\n"
            "Expected config/.env relative to project root."
        )

    _load_dotenv(dotenv_path)

    os.environ.setdefault(
        "PLAYLISTARR_RUN_ID",
        datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
    )
    os.environ.setdefault("PLAYLISTARR_BOOTSTRAPPED", "1")

    reset_env_caches()
    _BOOTSTRAPPED = True


def bootstrap_run_context(
    *,
    command: str,
    profile_name: str | None = None,
    verbose: bool | None = None,
    quiet: bool | None = None,
    interactive: bool | None = None,
) -> None:
    """Establish run-scoped context used by logging + pipeline stages."""

    os.environ["PLAYLISTARR_COMMAND"] = command

    if profile_name:
        os.environ["PLAYLISTARR_PROFILE_NAME"] = profile_name
    else:
        os.environ.pop("PLAYLISTARR_PROFILE_NAME", None)

    if verbose is not None:
        os.environ["PLAYLISTARR_VERBOSE"] = "1" if verbose else "0"
    if quiet is not None:
        os.environ["PLAYLISTARR_QUIET"] = "1" if quiet else "0"

    if interactive is not None:
        os.environ["PLAYLISTARR_UI"] = "1" if interactive else "0"

    # Context changes must invalidate cached env views.
    reset_env_caches()
