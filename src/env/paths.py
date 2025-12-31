from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------
# Project root
# ---------------------------------------------------------------------

# This file lives in src/, so project root is one level up
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------
# Base directories (override-friendly)
# ---------------------------------------------------------------------


def _resolve_dir(env_var: str, default: Path) -> Path:
    """
    Resolve a directory path from an environment variable or default.
    Ensures the directory exists.
    """
    raw = os.environ.get(env_var)
    path = Path(raw).expanduser().resolve() if raw else default
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------
# Public paths
# ---------------------------------------------------------------------

# Logs
LOGS_DIR = _resolve_dir(
    "PLAYLISTARR_LOGS_DIR",
    PROJECT_ROOT / "logs",
)

# Auth (OAuth tokens, client secrets)
AUTH_DIR = _resolve_dir(
    "PLAYLISTARR_AUTH_DIR",
    PROJECT_ROOT / "auth",
)

# Cache (discovery results, intermediate artifacts)
CACHE_DIR = _resolve_dir(
    "PLAYLISTARR_CACHE_DIR",
    PROJECT_ROOT / "cache",
)

# Output (reports, exports, future artifacts)
OUT_DIR = _resolve_dir(
    "PLAYLISTARR_OUT_DIR",
    PROJECT_ROOT / "out",
)

# Profiles (CSV definitions)
PROFILES_DIR = _resolve_dir(
    "PLAYLISTARR_PROFILES_DIR",
    PROJECT_ROOT / "profiles",
)


# ---------------------------------------------------------------------
# Utility / internal paths
# ---------------------------------------------------------------------


def auth_token_file(filename: str = "oauth_token.json") -> Path:
    """
    Path to an auth token file inside AUTH_DIR.
    """
    return AUTH_DIR / filename


def auth_client_secrets_file(filename: str = "client_secret.json") -> Path:
    """
    Path to an OAuth client secrets file inside AUTH_DIR.
    """
    return AUTH_DIR / filename


def cache_file(name: str) -> Path:
    """
    Path to a named cache file.
    """
    return CACHE_DIR / name


def out_file(name: str) -> Path:
    """
    Path to a named output file.
    """
    return OUT_DIR / name


# ---------------------------------------------------------------------
# Log layout helpers (used later by logger)
# ---------------------------------------------------------------------


def module_logs_dir(module: str) -> Path:
    """
    Base log directory for a CLI module (e.g. sync, auth).
    """
    path = LOGS_DIR / module
    path.mkdir(parents=True, exist_ok=True)
    return path


def profile_logs_dir(module: str, profile: str) -> Path:
    """
    Log directory for a specific profile under a module.
    """
    path = LOGS_DIR / module / profile
    path.mkdir(parents=True, exist_ok=True)
    return path
