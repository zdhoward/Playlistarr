from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = PROJECT_ROOT / "profiles"

# ------------------------------------------------------------
# Minimal dotenv loader (read-only helper, bootstrap owns usage)
# ------------------------------------------------------------


def _load_dotenv(path: Path) -> None:
    """
    Minimal dotenv loader.
    - Silent
    - Never overrides existing os.environ
    """
    if not path.exists():
        return

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()

        # strip inline comments
        if " #" in v:
            v = v.split(" #", 1)[0].rstrip()
        elif "\t#" in v:
            v = v.split("\t#", 1)[0].rstrip()

        # strip quotes
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
            v = v[1:-1]

        if k and k not in os.environ:
            os.environ[k] = v


# ------------------------------------------------------------
# Logs path (logger depends on this)
# ------------------------------------------------------------

LOGS_DIR = (
    Path(os.environ.get("PLAYLISTARR_LOGS_DIR", PROJECT_ROOT / "logs"))
    .expanduser()
    .resolve()
)

# ------------------------------------------------------------
# Errors / helpers
# ------------------------------------------------------------


class ConfigError(RuntimeError):
    pass


def _require(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise ConfigError(f"Missing required environment variable: {name}")
    return v


def _as_bool(v: str) -> bool:
    return v.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(v: str, default: int) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _as_float(v: str, default: float) -> float:
    try:
        return float(v)
    except Exception:
        return default


# ------------------------------------------------------------
# Logging environment (SAFE ANYWHERE)
# ------------------------------------------------------------


@dataclass(frozen=True)
class LoggingEnvironment:
    log_level: str
    log_retention: int
    verbose: bool
    quiet: bool
    interactive: bool


def get_logging_env() -> LoggingEnvironment:
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    log_retention = _as_int(os.environ.get("LOG_RETENTION", "30"), 30)

    verbose = _as_bool(os.environ.get("PLAYLISTARR_VERBOSE", "0"))
    quiet = _as_bool(os.environ.get("PLAYLISTARR_QUIET", "0"))

    no_ui = _as_bool(os.environ.get("PLAYLISTARR_NO_UI", "0"))
    ui_requested = _as_bool(os.environ.get("PLAYLISTARR_UI", "0"))

    interactive = ui_requested and not quiet and not no_ui and sys.stdout.isatty()

    return LoggingEnvironment(
        log_level=log_level,
        log_retention=log_retention,
        verbose=verbose,
        quiet=quiet,
        interactive=interactive,
    )


# ------------------------------------------------------------
# Full runtime environment (PIPELINE ONLY)
# ------------------------------------------------------------


class Environment:
    def __init__(self):
        # Logging snapshot (immutable)
        self._logging = get_logging_env()

        # ---- REQUIRED API ----
        self.youtube_api_keys = [
            k.strip() for k in _require("YOUTUBE_API_KEYS").split(",") if k.strip()
        ]

        self.country_code = os.environ.get("YOUTUBE_COUNTRY_CODE", "US")

        self.sleep_sec = _as_float(os.environ.get("YT_SLEEP_SEC", "0.2"), 0.2)
        self.request_timeout = _as_int(os.environ.get("YT_REQUEST_TIMEOUT", "30"), 30)
        self.max_retries = _as_int(os.environ.get("YT_MAX_RETRIES", "5"), 5)

        # ---- PIPELINE CONTEXT ----
        self.command = os.environ.get("PLAYLISTARR_COMMAND", "bootstrap")
        self.profile_name = os.environ.get(
            "PLAYLISTARR_PROFILE_NAME"
        ) or os.environ.get("PLAYLISTARR_PROFILE")
        self.profile_path = os.environ.get("PLAYLISTARR_PROFILE_PATH", "")
        self.artists_csv = os.environ.get("PLAYLISTARR_ARTISTS_CSV", "")
        self.playlist_id = os.environ.get("PLAYLISTARR_PLAYLIST_ID", "")

        self.max_add = _as_int(os.environ.get("PLAYLISTARR_MAX_ADD", "0"), 0)
        self.progress_every = _as_int(
            os.environ.get("PLAYLISTARR_PROGRESS_EVERY", "50"), 50
        )

        # ---- PIPELINE FLAGS ----
        self.force_update = _as_bool(os.environ.get("PLAYLISTARR_FORCE_UPDATE", "0"))
        self.dry_run = _as_bool(os.environ.get("PLAYLISTARR_DRY_RUN", "0"))
        self.no_filter = _as_bool(os.environ.get("PLAYLISTARR_NO_FILTER", "0"))

    def as_dict(self) -> dict:
        return {
            "Logging": {
                "log_level": self.log_level,
                "log_retention": self.log_retention,
                "verbose": self.verbose,
                "quiet": self.quiet,
                "interactive": self.interactive,
            },
            "Pipeline": {
                "command": self.command,
                "profile_name": self.profile_name,
                "profile_path": self.profile_path,
                "artists_csv": self.artists_csv,
                "playlist_id": self.playlist_id,
            },
            "Behavior": {
                "dry_run": self.dry_run,
                "force_update": self.force_update,
                "no_filter": self.no_filter,
                "max_add": self.max_add,
                "progress_every": self.progress_every,
            },
            "API": {
                "youtube_api_keys": f"{len(self.youtube_api_keys)} keys loaded",
                "country_code": self.country_code,
            },
        }

    # ---- logging passthrough ----
    @property
    def log_level(self) -> str:
        return self._logging.log_level

    @property
    def log_retention(self) -> int:
        return self._logging.log_retention

    @property
    def verbose(self) -> bool:
        return self._logging.verbose

    @property
    def quiet(self) -> bool:
        return self._logging.quiet

    @property
    def interactive(self) -> bool:
        return self._logging.interactive


_ENV: Optional[Environment] = None


def reset_env_caches() -> None:
    """Invalidate cached views of environment variables."""
    global _ENV
    _ENV = None


def get_env() -> Environment:
    global _ENV
    if _ENV is None:
        _ENV = Environment()
    return _ENV
