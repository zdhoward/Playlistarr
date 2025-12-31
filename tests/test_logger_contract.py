import logging


def test_logger_initializes(monkeypatch):
    monkeypatch.setenv("PLAYLISTARR_COMMAND", "test")

    from logger import init_logging, get_logger

    init_logging()
    log = get_logger("test")

    assert isinstance(log, logging.Logger)


def test_logger_console_output(capsys, monkeypatch):
    monkeypatch.setenv("PLAYLISTARR_COMMAND", "test")

    from logger import init_logging, get_logger

    init_logging()
    get_logger("test").info("hello")

    out = capsys.readouterr()
    assert "hello" in out.err
