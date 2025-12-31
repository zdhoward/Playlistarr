from __future__ import annotations

import json
import os
from typing import Optional, Dict, Any

_UI_PREFIX = "__PLAYLISTARR_UI__ "


def ui_events_enabled() -> bool:
    return os.environ.get("PLAYLISTARR_UI") == "1"


def emit_ui_event(event: str, **payload: Any) -> None:
    if not ui_events_enabled():
        return

    msg = {"event": event, **payload}
    print(_UI_PREFIX + json.dumps(msg), flush=True)


def try_parse_ui_event(line: str) -> Optional[Dict[str, Any]]:
    if not line.startswith(_UI_PREFIX):
        return None

    try:
        return json.loads(line[len(_UI_PREFIX) :])
    except Exception:
        return None
