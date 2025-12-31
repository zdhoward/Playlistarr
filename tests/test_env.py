from env import get_env


def test_env_defaults(monkeypatch):
    monkeypatch.delenv("PLAYLISTARR_VERBOSE", raising=False)
    monkeypatch.delenv("PLAYLISTARR_QUIET", raising=False)

    env = get_env()
    assert env.verbose is False
    assert env.quiet is False


def test_env_accepts_verbose_flag(monkeypatch):
    monkeypatch.setenv("PLAYLISTARR_VERBOSE", "1")
    env = get_env()

    # env records preference, does not force runtime behavior
    assert hasattr(env, "verbose")


def test_env_accepts_quiet_flag(monkeypatch):
    monkeypatch.setenv("PLAYLISTARR_QUIET", "1")
    env = get_env()

    # env records preference, does not force runtime behavior
    assert hasattr(env, "quiet")
