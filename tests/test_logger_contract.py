import logging


def test_logger_initializes(monkeypatch):
    monkeypatch.setenv("PLAYLISTARR_COMMAND", "test")
    monkeypatch.setenv("PLAYLISTARR_VERBOSE", "1")

    from logger import init_logging, get_logger

    init_logging(module="test")
    log = get_logger("test")

    assert isinstance(log, logging.Logger)


def test_logger_console_output(capsys, monkeypatch):
    monkeypatch.setenv("PLAYLISTARR_COMMAND", "test")
    monkeypatch.setenv("PLAYLISTARR_VERBOSE", "1")

    from logger import init_logging, get_logger

    init_logging(module="test")
    get_logger("test").info("hello")

    out = capsys.readouterr()

    # RichHandler writes to stdout
    assert "hello" in out.out
