from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Iterable

from env import PROFILES_DIR
from cli.common import dispatch_subparser_help


def build_profiles_parser(subparsers: argparse._SubParsersAction) -> None:
    profiles = subparsers.add_parser("profiles", help="Manage playlist profiles")
    psub = profiles.add_subparsers(dest="profiles_cmd", required=True)

    help_p = psub.add_parser("help", help="Show help for profiles")
    help_p.add_argument("path", nargs="*", help="Subcommand path (e.g. add, edit)")
    help_p.set_defaults(action="help", _help_parser=profiles)

    list_p = psub.add_parser("list", help="List profiles")
    list_p.set_defaults(action="list")

    show = psub.add_parser("show", help="Show a profile (paths + JSON)")
    show.add_argument("name", help="Profile name")
    show.set_defaults(action="show")

    add = psub.add_parser("add", help="Add a new profile")
    add.add_argument("name", help="Profile name")
    add.add_argument("--playlist", required=True, help="YouTube playlist ID")
    add.add_argument("--label", help="Display label (defaults to name)")
    add.set_defaults(action="add")

    edit = psub.add_parser("edit", help="Edit an existing profile")
    edit.add_argument("name", help="Profile name")
    edit.add_argument("--playlist", help="New playlist ID")
    edit.add_argument("--label", help="New label")
    edit.set_defaults(action="edit")

    rm = psub.add_parser("remove", help="Remove a profile")
    rm.add_argument("name", help="Profile name")
    rm.set_defaults(action="remove")

    clone = psub.add_parser("clone", help="Clone an existing profile")
    clone.add_argument("source", help="Source profile name")
    clone.add_argument("dest", help="New profile name")
    clone.add_argument("--playlist", help="Override playlist ID")
    clone.add_argument("--label", help="Override label")
    clone.set_defaults(action="clone")

    validate = psub.add_parser("validate", help="Validate profiles")
    validate.add_argument("name", nargs="?", help="Profile name (omit to validate all profiles)")
    validate.set_defaults(action="validate")


def _profile_paths(name: str) -> tuple[Path, Path]:
    return (PROFILES_DIR / f"{name}.json", PROFILES_DIR / f"{name}.csv")


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"{path.name}: invalid JSON ({e})") from e


def _iter_profiles() -> Iterable[str]:
    for p in sorted(PROFILES_DIR.glob("*.json")):
        yield p.stem


def _read_artists_csv(path: Path) -> list[str]:
    """
    Accept either:
      - headerless 1-column list (preferred)
      - OR a header row containing 'artist' (legacy/optional)

    Returns normalized, non-empty artist strings.
    """
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    raw = [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]
    if not raw:
        return []

    if raw[0].strip().lower() == "artist":
        raw = raw[1:]

    artists: list[str] = []
    for ln in raw:
        cell = ln.split(",", 1)[0].strip()
        if cell:
            artists.append(cell)

    return artists


def handle_profiles(args: argparse.Namespace) -> int:
    PROFILES_DIR.mkdir(exist_ok=True)

    if args.action == "help":
        parser: argparse.ArgumentParser = args._help_parser
        return dispatch_subparser_help(parser, list(getattr(args, "path", []) or []))

    action = args.action

    if action == "list":
        for name in _iter_profiles():
            print(name)
        return 0

    if action == "show":
        json_path, csv_path = _profile_paths(args.name)
        if not json_path.exists():
            raise SystemExit(f"Profile '{args.name}' does not exist")

        data = _load_json(json_path)

        print(f"Profile:   {args.name}")
        print(f"JSON:      {json_path}")
        print(f"CSV:       {csv_path}")
        print(f"playlist:  {(data.get('playlist_id') or '').strip()}")
        print(f"label:     {(data.get('label') or '').strip()}")
        print("rules:     present" if isinstance(data.get("rules"), dict) else "rules:     missing/invalid")
        if csv_path.exists():
            artists = _read_artists_csv(csv_path)
            print(f"artists:   {len(artists)}")
        else:
            print("artists:   (missing csv)")
        print("")
        print(json.dumps(data, indent=2))
        return 0

    if action == "add":
        json_path, csv_path = _profile_paths(args.name)

        if json_path.exists() or csv_path.exists():
            raise SystemExit(f"Profile '{args.name}' already exists")

        json_path.write_text(
            json.dumps(
                {"label": args.label or args.name, "playlist_id": args.playlist, "rules": {}},
                indent=2,
            ),
            encoding="utf-8",
        )

        csv_path.write_text("", encoding="utf-8")

        print(f"Profile '{args.name}' created")
        return 0

    if action == "edit":
        json_path, _ = _profile_paths(args.name)

        if not json_path.exists():
            raise SystemExit(f"Profile '{args.name}' does not exist")

        data = _load_json(json_path)

        if args.playlist:
            data["playlist_id"] = args.playlist
        if args.label:
            data["label"] = args.label

        json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Profile '{args.name}' updated")
        return 0

    if action == "remove":
        json_path, csv_path = _profile_paths(args.name)

        if json_path.exists():
            json_path.unlink()
        if csv_path.exists():
            csv_path.unlink()

        print(f"Profile '{args.name}' removed")
        return 0

    if action == "clone":
        src_json, src_csv = _profile_paths(args.source)
        dst_json, dst_csv = _profile_paths(args.dest)

        if not src_json.exists() or not src_csv.exists():
            raise SystemExit(f"Source profile '{args.source}' does not exist")

        if dst_json.exists() or dst_csv.exists():
            raise SystemExit(f"Destination profile '{args.dest}' already exists")

        shutil.copy2(src_csv, dst_csv)

        data = _load_json(src_json)
        if args.playlist:
            data["playlist_id"] = args.playlist
        if args.label:
            data["label"] = args.label

        dst_json.write_text(json.dumps(data, indent=2), encoding="utf-8")

        print(f"Profile '{args.source}' cloned to '{args.dest}'")
        return 0

    if action == "validate":
        names = [args.name] if args.name else list(_iter_profiles())
        if not names:
            print("No profiles found")
            return 0

        ok = True

        for name in names:
            json_path, csv_path = _profile_paths(name)
            print(f"\n{name}:")

            if not json_path.exists():
                print("  ✗ missing JSON file")
                ok = False
                continue

            try:
                data = _load_json(json_path)
                print("  ✓ JSON valid")
            except ValueError as e:
                print(f"  ✗ {e}")
                ok = False
                continue

            playlist_id = (data.get("playlist_id") or "").strip()
            if playlist_id:
                print("  ✓ playlist_id present")
            else:
                print("  ✗ missing playlist_id")
                ok = False

            if not csv_path.exists():
                print("  ✗ missing CSV file")
                ok = False
                continue

            try:
                artists = _read_artists_csv(csv_path)
                if not artists:
                    print("  ✗ CSV has no artists")
                    ok = False
                else:
                    print(f"  ✓ CSV valid ({len(artists)} artists)")
            except Exception as e:
                print(f"  ✗ CSV unreadable ({e})")
                ok = False

        return 0 if ok else 1

    raise SystemExit(f"Unknown profiles action: {action}")
