def test_logger_creates_file(tmp_path, monkeypatch):
    monkeypatch.setenv("PLAYLISTARR_LOGS_DIR", str(tmp_path))
    monkeypatch.setenv("PLAYLISTARR_COMMAND", "auth")

    from logger import init_logging, get_logger

    init_logging()
    get_logger("test").info("hello")

    assert any(tmp_path.rglob("*.log"))
