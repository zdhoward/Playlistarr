def test_retention_prunes_old_logs(tmp_path):
    from logger.retention import enforce_retention

    for i in range(5):
        (tmp_path / f"{i}.log").write_text("x")

    enforce_retention(tmp_path, keep=2)

    remaining = list(tmp_path.glob("*.log"))
    assert len(remaining) == 2
