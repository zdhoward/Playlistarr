"""
utils.py

Path utilities and helper functions.

This module provides:
- Path generation with validation
- Common file I/O operations
- Safe directory creation
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

import config


# ============================================================
# Path Validation
# ============================================================


def validate_playlist_id(playlist_id: str) -> None:
    """
    Validate playlist ID format to prevent path traversal.

    Args:
        playlist_id: YouTube playlist ID

    Raises:
        ValueError: If playlist_id contains invalid characters
    """
    if not re.match(r"^[A-Za-z0-9_-]+$", playlist_id):
        raise ValueError(
            f"Invalid playlist_id: {playlist_id}. "
            f"Must contain only alphanumeric characters, hyphens, and underscores."
        )


def validate_artist_name(artist: str) -> None:
    """
    Validate artist name for use in filesystem paths.

    Args:
        artist: Artist name

    Raises:
        ValueError: If artist name contains invalid characters
    """
    if not artist or not artist.strip():
        raise ValueError("Artist name cannot be empty")

    # Check for path traversal attempts (but allow / in names like AC/DC)
    if ".." in artist:
        raise ValueError(
            f"Invalid artist name: {artist}. "
            f"Cannot contain parent directory references (..)."
        )

    # Check for actual path separators when used as path components
    # We sanitize / and \ by replacing them with safe alternatives
    # This is handled in the path generation, not validation


# ============================================================
# Path Generators
# ============================================================


def playlist_cache_path(playlist_id: str) -> Path:
    """
    Get the cache file path for a playlist.

    Args:
        playlist_id: YouTube playlist ID

    Returns:
        Path to playlist cache JSON file

    Raises:
        ValueError: If playlist_id is invalid
    """
    validate_playlist_id(playlist_id)
    Path(config.CACHE_DIR).mkdir(parents=True, exist_ok=True)
    return Path(config.CACHE_DIR) / f"playlist_{playlist_id}.json"


def invalidation_plan_path(playlist_id: str) -> Path:
    """
    Get the invalidation plan file path for a playlist.

    Args:
        playlist_id: YouTube playlist ID

    Returns:
        Path to invalidation plan JSON file

    Raises:
        ValueError: If playlist_id is invalid
    """
    validate_playlist_id(playlist_id)
    Path(config.CACHE_DIR).mkdir(parents=True, exist_ok=True)
    return Path(config.CACHE_DIR) / f"invalidation_{playlist_id}.json"


def discovery_output_path(csv_stem: str, artist: str) -> Path:
    """
    Get the discovery output directory for an artist.

    Args:
        csv_stem: CSV filename stem (e.g., "artists" from "artists.csv")
        artist: Artist name

    Returns:
        Path to artist's discovery output directory

    Raises:
        ValueError: If artist name is invalid
    """
    validate_artist_name(artist)

    # Sanitize artist name for filesystem use
    # Replace slashes with dashes (e.g., "AC/DC" -> "AC-DC")
    safe_artist = artist.replace("/", "-").replace("\\", "-")

    # Remove other problematic characters for Windows
    # Windows reserved: < > : " | ? *
    for char in '<>:"|?*':
        safe_artist = safe_artist.replace(char, "-")

    out_root = Path(config.DISCOVERY_ROOT) / csv_stem / safe_artist
    out_root.mkdir(parents=True, exist_ok=True)
    return out_root


# ============================================================
# File I/O Helpers
# ============================================================


def read_json(path: Path) -> Any:
    """
    Safely read and parse a JSON file.

    Args:
        path: Path to JSON file

    Returns:
        Parsed JSON data

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any, atomic: bool = True) -> None:
    """
    Safely write data to a JSON file.

    Args:
        path: Path to JSON file
        data: Data to serialize
        atomic: If True, write to temp file first then rename (safer)

    Raises:
        TypeError: If data is not JSON serializable
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    if atomic:
        # Write to temporary file first
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)

        # Atomic rename
        tmp_path.replace(path)
    else:
        # Direct write
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)


def read_json_safe(path: Path, default: Any = None) -> Any:
    """
    Read JSON file, returning default value if file doesn't exist or is invalid.

    Args:
        path: Path to JSON file
        default: Value to return if file cannot be read

    Returns:
        Parsed JSON data or default value
    """
    try:
        return read_json(path)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


# ============================================================
# Directory Helpers
# ============================================================


def ensure_directory(path: Path) -> None:
    """
    Ensure directory exists, creating it if necessary.

    Args:
        path: Directory path
    """
    path.mkdir(parents=True, exist_ok=True)


def safe_mkdir(path: Path) -> None:
    """
    Legacy alias for ensure_directory.

    Args:
        path: Directory path
    """
    ensure_directory(path)
