import logging
import sys
import pytest


@pytest.fixture(autouse=True)
def clean_env_and_modules(monkeypatch):
    """
    Ensure tests don't leak env, logger state, or cached path resolution.
    """

    keys = [
        "PLAYLISTARR_LOGS_DIR",
        "PLAYLISTARR_AUTH_DIR",
        "PLAYLISTARR_CACHE_DIR",
        "PLAYLISTARR_OUT_DIR",
        "PLAYLISTARR_COMMAND",
        "PLAYLISTARR_PROFILE",
        "PLAYLISTARR_PROFILE_NAME",
        "PLAYLISTARR_RUN_ID",
        "PLAYLISTARR_VERBOSE",
        "PLAYLISTARR_QUIET",
        "PLAYLISTARR_ARTISTS_CSV",
        "PLAYLISTARR_PLAYLIST_ID",
        "PLAYLISTARR_UI",
    ]
    for k in keys:
        monkeypatch.delenv(k, raising=False)

    # Minimal required env
    monkeypatch.setenv("PLAYLISTARR_ARTISTS_CSV", "dummy.csv")
    monkeypatch.setenv("PLAYLISTARR_PLAYLIST_ID", "DUMMY_PLAYLIST")

    # 🔑 Ensure UI never activates in tests
    monkeypatch.setenv("PLAYLISTARR_UI", "0")

    # Reset logger global state
    import logger.state

    logger.state.INITIALIZED = False
    logger.state.LOG_DIR = None
    logger.state.LOG_FILE_PATH = None

    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    # Force re-import of path + logger modules
    for mod in [
        "paths",
        "logger",
        "logger.state",
        "logger.context",
        "logger.log_paths",
        "logger.file",
        "logger.console",
        "logger.retention",
    ]:
        sys.modules.pop(mod, None)
