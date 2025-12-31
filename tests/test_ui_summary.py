from ui.state import UISummary


def test_ui_summary_tracks_stages():
    summary = UISummary()
    summary.stages["Discovery"] = "ok"
    summary.stages["Sync"] = "ok"

    assert summary.stages["Discovery"] == "ok"
    assert summary.stages["Sync"] == "ok"


def test_ui_summary_stop_reason():
    summary = UISummary()
    summary.stop_reason = "auth_invalid"

    assert summary.stop_reason == "auth_invalid"
