# src/env.py
from __future__ import annotations

import os
import sys
from pathlib import Path
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
LOGS_DIR = PROJECT_ROOT / "logs"

ENV_FILE = CONFIG_DIR / ".env"


# ============================================================
# Internal dotenv loader
# ============================================================


def _load_dotenv() -> None:
    """
    Load .env into os.environ without overwriting existing shell variables.
    CLI / Docker / CI always win.
    """
    if not ENV_FILE.exists():
        return

    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()

        if k not in os.environ:
            os.environ[k] = v


# Load .env once, immediately
_load_dotenv()


def _require(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise ConfigError(f"Missing required environment variable: {name}")
    return v


# ============================================================
# Logging-safe environment (bootstrap / CLI / auth)
# ============================================================


class LoggingEnvironment:
    """
    Minimal environment required for logging.
    MUST NOT require secrets or pipeline-specific variables.
    """

    def __init__(self):
        self.raw = dict(os.environ)

        self.log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        self.log_retention = int(os.environ.get("LOG_RETENTION", "10"))

        self.verbose = os.environ.get("PLAYLISTARR_VERBOSE", "0") == "1"
        self.quiet = os.environ.get("PLAYLISTARR_QUIET", "0") == "1"

        no_ui = os.environ.get("PLAYLISTARR_NO_UI", "0") == "1"
        self.interactive = (
            not self.verbose and not self.quiet and not no_ui and sys.stdout.isatty()
        )


_LOG_ENV: Optional[LoggingEnvironment] = None


def get_logging_env() -> LoggingEnvironment:
    """
    Return frozen logging-only environment.
    Safe in CLI help, auth, and CI contexts.
    """
    global _LOG_ENV
    if _LOG_ENV is None:
        _LOG_ENV = LoggingEnvironment()
    return _LOG_ENV


# ============================================================
# Full runtime environment (pipeline)
# ============================================================


class Environment(LoggingEnvironment):
    """
    Full runtime environment.
    Only valid once the pipeline is actually running.
    """

    def __init__(self):
        super().__init__()

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
        # Pipeline context (injected by CLI / runner)
        # ------------------------------------------------------------

        self.artists_csv = _require("PLAYLISTARR_ARTISTS_CSV")
        self.playlist_id = _require("PLAYLISTARR_PLAYLIST_ID")

        self.force_update = os.environ.get("PLAYLISTARR_FORCE_UPDATE", "0") == "1"
        self.no_filter = os.environ.get("PLAYLISTARR_NO_FILTER", "0") == "1"
        self.dry_run = os.environ.get("PLAYLISTARR_DRY_RUN", "0") == "1"

        self.max_add = int(os.environ.get("PLAYLISTARR_MAX_ADD", "0"))
        self.progress_every = int(os.environ.get("PLAYLISTARR_PROGRESS_EVERY", "50"))


_ENV: Optional[Environment] = None


def get_env() -> Environment:
    """
    Return frozen runtime environment.
    """
    global _ENV
    if _ENV is None:
        _ENV = Environment()
    return _ENV


# ============================================================
# Export to cmd.exe
# ============================================================


def export_cmd() -> None:
    """
    Used by run.cmd to import .env into Windows shell.
    """
    _load_dotenv()
