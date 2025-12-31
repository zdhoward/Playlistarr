from ui.state import UIState


def test_ui_state_defaults():
    state = UIState()

    assert state.stage == ""
    assert state.stage_index == 0
    assert state.stage_total == 0

    assert state.artist == ""
    assert state.task == ""

    assert state.progress_completed == 0
    assert state.progress_total == 0

    assert state.old_count is None
    assert state.new_count is None
    assert state.api_key_index is None
    assert state.api_key_total is None


def test_ui_state_progress_update():
    state = UIState()
    state.progress_total = 10
    state.progress_completed = 3

    assert state.progress_completed <= state.progress_total
