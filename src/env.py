from __future__ import annotations

from pathlib import Path
import os
from typing import Optional


# ============================================================
# Errors
# ============================================================

class ConfigError(RuntimeError):
    pass


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"
PROFILES_DIR = PROJECT_ROOT / "profiles"

ENV_FILE = CONFIG_DIR / ".env"

# ============================================================
# Internal dotenv loader
# ============================================================

def _load_dotenv() -> None:
    """
    Load .env into os.environ without overwriting existing shell variables.
    This allows run.cmd / docker / CI to override values.
    """
    if not ENV_FILE.exists():
        return

    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()

        # Never override shell / CLI values
        if k not in os.environ:
            os.environ[k] = v

# Load .env once into process env before anything else
_load_dotenv()

def _require(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise ConfigError(f"Missing required environment variable: {name}")
    return v


# ============================================================
# Environment object (frozen per run)
# ============================================================

class Environment:
    def __init__(self):
        # Snapshot raw environment for debugging
        self.raw = dict(os.environ)

        # ------------------------------------------------------------
        # Logging
        # ------------------------------------------------------------
        self.log_level = os.environ.get("LOG_LEVEL", "INFO")
        self.log_format = os.environ.get("LOG_FORMAT", "text")

        # Allow per-run override from run.cmd
        self.log_dir = os.environ.get(
            "PLAYLISTARR_RUN_LOG_DIR",
            os.environ.get("LOG_DIR", "../logs"),
        )

        self.log_retention = int(os.environ.get("LOG_RETENTION", "10"))

        # ------------------------------------------------------------
        # Core API
        # ------------------------------------------------------------
        self.youtube_api_keys = _require("YOUTUBE_API_KEYS").split(",")
        self.country_code = os.environ.get("YOUTUBE_COUNTRY_CODE", "US")

        self.sleep_sec = float(os.environ.get("YT_SLEEP_SEC", "0.2"))
        self.request_timeout = int(os.environ.get("YT_REQUEST_TIMEOUT", "30"))
        self.max_retries = int(os.environ.get("YT_MAX_RETRIES", "3"))
        self.backoff_base = float(os.environ.get("YT_BACKOFF_BASE_SEC", "1.0"))

        self.cache_ttl = int(os.environ.get("CACHE_TTL_SECONDS", "21600"))

        # ------------------------------------------------------------
        # Pipeline run context (injected by run.cmd)
        # ------------------------------------------------------------
        self.artists_csv = _require("PLAYLISTARR_ARTISTS_CSV")
        self.playlist_id = _require("PLAYLISTARR_PLAYLIST_ID")

        self.force_update = os.environ.get("PLAYLISTARR_FORCE_UPDATE", "0") == "1"
        self.no_filter = os.environ.get("PLAYLISTARR_NO_FILTER", "0") == "1"
        self.dry_run = os.environ.get("PLAYLISTARR_DRY_RUN", "0") == "1"

        self.max_add = int(os.environ.get("PLAYLISTARR_MAX_ADD", "0"))
        self.progress_every = int(os.environ.get("PLAYLISTARR_PROGRESS_EVERY", "50"))

        self.verbose = os.environ.get("PLAYLISTARR_VERBOSE", "0") == "1"
        self.quiet = os.environ.get("PLAYLISTARR_QUIET", "0") == "1"


# ============================================================
# Frozen singleton
# ============================================================

_ENV: Optional[Environment] = None


def get_env() -> Environment:
    """
    Return the frozen Environment for this run.
    .env is loaded only once and never re-read.
    """
    global _ENV
    if _ENV is None:
        _ENV = Environment()
    return _ENV


# ============================================================
# Export to cmd.exe
# ============================================================

def export_cmd():
    """
    Used by run.cmd to import .env into Windows shell.
    """
    _load_dotenv()
