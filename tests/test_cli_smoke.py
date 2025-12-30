import subprocess
import sys


def test_auth_help_runs():
    result = subprocess.run(
        [sys.executable, "-m", "playlistarr", "auth", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


def test_sync_help_runs():
    result = subprocess.run(
        [sys.executable, "-m", "playlistarr", "sync", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
