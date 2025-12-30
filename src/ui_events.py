from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict


_UI_PREFIX = "__PLAYLISTARR_UI__ "


def ui_events_enabled() -> bool:
    # Runner sets this when interactive UI is active.
    return os.environ.get("PLAYLISTARR_UI", "0") == "1"


def emit_ui_event(event: str, **fields: Any) -> None:
    """Emit a single-line UI event for the runner to consume.

    This is intentionally stdout-based (not logging-based) so stages can remain
    fully quiet on the console while still providing progress signals.

    Format:
      __PLAYLISTARR_UI__ {json}

    If UI events are disabled, this is a no-op.
    """
    if not ui_events_enabled():
        return

    payload: Dict[str, Any] = {"event": event, **fields}
    try:
        line = _UI_PREFIX + json.dumps(
            payload, ensure_ascii=False, separators=(",", ":")
        )
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
    except Exception:
        # Never let UI signaling affect pipeline correctness.
        return


def try_parse_ui_event(line: str) -> Dict[str, Any] | None:
    """Parse a UI event line emitted by emit_ui_event()."""
    if not line.startswith(_UI_PREFIX):
        return None
    raw = line[len(_UI_PREFIX) :].strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data
