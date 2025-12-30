#!/usr/bin/env python3
import sys
import json
import shutil
from pathlib import Path
import argparse

# Make project root importable so we can import utils.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils import canonicalize_artist


def read_display_name(artist_dir: Path) -> str | None:
    summary = artist_dir / "summary.json"
    if not summary.exists():
        return None
    try:
        with summary.open("r", encoding="utf-8") as f:
            return json.load(f).get("artist")
    except Exception:
        return None


def merge_dirs(src: Path, dst: Path):
    """
    Merge src into dst safely.
    Keeps the newest version of any colliding files.
    Removes src completely afterward.
    """
    for item in src.iterdir():
        target = dst / item.name

        if not target.exists():
            shutil.move(str(item), str(target))
        else:
            # Both exist — keep the newer one
            try:
                src_mtime = item.stat().st_mtime
                dst_mtime = target.stat().st_mtime
            except FileNotFoundError:
                continue

            if src_mtime > dst_mtime:
                if target.is_file():
                    target.unlink()
                else:
                    shutil.rmtree(target)
                shutil.move(str(item), str(target))
            else:
                # Destination is newer — discard source
                if item.is_file():
                    item.unlink()
                else:
                    shutil.rmtree(item)

    # Remove the now-empty source directory
    shutil.rmtree(src)


def main():
    parser = argparse.ArgumentParser(description="Migrate artist folders to canonical keys (merge-safe)")
    parser.add_argument("csv_stem", help="CSV stem, e.g. 'muchloud_artists'")
    parser.add_argument("--apply", action="store_true", help="Perform changes (default is dry-run)")
    args = parser.parse_args()

    root = Path("out") / args.csv_stem
    if not root.exists():
        raise RuntimeError(f"Discovery root not found: {root}")

    planned = []

    for d in root.iterdir():
        if not d.is_dir():
            continue

        display = read_display_name(d)
        if not display:
            continue

        key = canonicalize_artist(display)
        if not key or key == d.name:
            continue

        target = root / key
        planned.append((d, target, display))

    if not planned:
        logger.debug("All folders already canonical.")
        return

    logger.debug("\nPlanned migrations:")
    for src, dst, name in planned:
        if dst.exists():
            logger.debug(f"  MERGE  {src.name} → {dst.name}   ({name})")
        else:
            logger.debug(f"  RENAME {src.name} → {dst.name}   ({name})")

    if not args.apply:
        logger.debug("\nDRY RUN — nothing changed.")
        logger.debug("Re-run with --apply to perform migration.")
        return

    logger.debug("\nApplying migrations...")
    for src, dst, name in planned:
        if dst.exists():
            merge_dirs(src, dst)
            logger.debug(f"Merged {src.name} → {dst.name}")
        else:
            shutil.move(str(src), str(dst))
            logger.debug(f"Renamed {src.name} → {dst.name}")

    logger.debug("\nMigration complete.")


if __name__ == "__main__":
    main()
