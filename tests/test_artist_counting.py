from pathlib import Path
from runner import _count_artists


def test_count_artists_simple(tmp_path):
    p = tmp_path / "artists.csv"
    p.write_text("artist\nA\nB\nC\n")

    assert _count_artists(p) == 3


def test_count_artists_ignores_blank_lines(tmp_path):
    p = tmp_path / "artists.csv"
    p.write_text("artist\n\nA\n\nB\n")

    assert _count_artists(p) == 2
