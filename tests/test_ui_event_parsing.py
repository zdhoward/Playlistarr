from ui.events import try_parse_ui_event


def test_parse_valid_ui_event():
    line = '__PLAYLISTARR_UI__ {"event": "task", "task": "hello"}'
    evt = try_parse_ui_event(line)

    assert evt is not None
    assert evt["event"] == "task"
    assert evt["task"] == "hello"


def test_ignore_non_ui_lines():
    assert try_parse_ui_event("hello world") is None


def test_invalid_json_safe():
    assert try_parse_ui_event("__PLAYLISTARR_UI__ {bad json}") is None
