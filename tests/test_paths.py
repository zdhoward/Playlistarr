def test_logs_dir_default(tmp_path, monkeypatch):
    monkeypatch.setenv("PLAYLISTARR_LOGS_DIR", str(tmp_path / "logs"))

    import paths

    assert paths.LOGS_DIR.exists()


def test_paths_respect_env_overrides(tmp_path, monkeypatch):
    monkeypatch.setenv("PLAYLISTARR_LOGS_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("PLAYLISTARR_AUTH_DIR", str(tmp_path / "auth"))
    monkeypatch.setenv("PLAYLISTARR_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("PLAYLISTARR_OUT_DIR", str(tmp_path / "out"))

    import paths

    assert paths.LOGS_DIR.exists()
    assert paths.AUTH_DIR.exists()
    assert paths.CACHE_DIR.exists()
    assert paths.OUT_DIR.exists()


def test_log_path_helpers(tmp_path, monkeypatch):
    monkeypatch.setenv("PLAYLISTARR_LOGS_DIR", str(tmp_path))

    import paths

    mod = paths.module_logs_dir("auth")
    prof = paths.profile_logs_dir("sync", "testprofile")

    assert mod.exists()
    assert prof.exists()
    assert prof.parent.name == "sync"
