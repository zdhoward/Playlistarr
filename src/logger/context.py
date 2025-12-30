from __future__ import annotations

import os
from datetime import datetime
from typing import Optional


def resolve_run_id() -> str:
    run_id = os.environ.get("PLAYLISTARR_RUN_ID")
    if not run_id:
        run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        os.environ["PLAYLISTARR_RUN_ID"] = run_id
    return run_id


def resolve_command() -> str:
    return os.environ.get("PLAYLISTARR_COMMAND") or "bootstrap"


def resolve_profile() -> Optional[str]:
    return os.environ.get("PLAYLISTARR_PROFILE") or os.environ.get(
        "PLAYLISTARR_PROFILE_NAME"
    )
