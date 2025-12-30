def test_logger_creates_module_log(tmp_path, monkeypatch):
    monkeypatch.setenv("PLAYLISTARR_LOGS_DIR", str(tmp_path))
    monkeypatch.setenv("PLAYLISTARR_COMMAND", "auth")

    from logger import init_logging, get_logger

    init_logging()
    get_logger("test").info("hello")

    logs = list(tmp_path.rglob("*.log"))
    assert len(logs) == 1
    assert "auth" in logs[0].name


def test_logger_profile_scoped(tmp_path, monkeypatch):
    monkeypatch.setenv("PLAYLISTARR_LOGS_DIR", str(tmp_path))
    monkeypatch.setenv("PLAYLISTARR_COMMAND", "sync")
    monkeypatch.setenv("PLAYLISTARR_PROFILE", "demo")

    from logger import init_logging, get_logger

    init_logging()
    get_logger("test").info("hello")

    logs = list(tmp_path.rglob("*.log"))
    assert logs
    assert "sync" in logs[0].parts
    assert "demo" in logs[0].parts
