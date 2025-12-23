"""
config.py

Central configuration for Playlistarr.

This file intentionally contains ONLY:
- Constants
- Tunables
- Keyword lists
- Regex patterns
- File paths

It must NOT contain:
- Business logic
- API calls
- Helper functions

Logic belongs in:
- filters.py
- client.py
- calling scripts
"""

from dotenv import load_dotenv

load_dotenv()

import os
import sys
import re
from pathlib import Path
from typing import Dict, List

# Windows compatibility - ensure UTF-8 encoding
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# ============================================================
# FILESYSTEM PATHS
# ============================================================
# All paths are relative to project root.

AUTH_DIR = "auth"
CACHE_DIR = "cache"
DISCOVERY_ROOT = "out"

CLIENT_SECRETS_FILE = f"{AUTH_DIR}/client_secrets.json"
OAUTH_TOKEN_FILE = f"{AUTH_DIR}/oauth_token.json"

PLAYLIST_CACHE_FILE = f"{CACHE_DIR}/playlist_cache.json"


# ============================================================
# YouTube API — AUTH & ENDPOINTS
# ============================================================


def _load_api_keys() -> List[str]:
    """Load API keys from environment variable."""
    keys_str = os.environ.get("YOUTUBE_API_KEYS", "")
    if not keys_str:
        raise ValueError(
            "YOUTUBE_API_KEYS environment variable not set. "
            "Set it as comma-separated keys: export YOUTUBE_API_KEYS='key1,key2,key3'"
        )
    keys = [k.strip() for k in keys_str.split(",") if k.strip()]
    if not keys:
        raise ValueError("YOUTUBE_API_KEYS is empty after parsing")
    return keys


API_KEYS = _load_api_keys()

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"

YOUTUBE_OAUTH_SCOPES = ["https://www.googleapis.com/auth/youtube"]

COUNTRY_CODE = os.environ.get("YOUTUBE_COUNTRY_CODE", "CA")

# ============================================================
# YOUTUBE API — SAFETY / THROTTLING
# ============================================================

SLEEP_BETWEEN_CALLS_SEC = float(os.environ.get("YT_SLEEP_SEC", "0.15"))
REQUEST_TIMEOUT = int(os.environ.get("YT_REQUEST_TIMEOUT", "30"))
MAX_RETRIES = int(os.environ.get("YT_MAX_RETRIES", "3"))
BACKOFF_BASE_SEC = float(os.environ.get("YT_BACKOFF_BASE_SEC", "1.0"))

# ============================================================
# DISCOVERY — CHANNEL RESOLUTION
# ============================================================

MIN_UPLOADS_FOR_VIABLE_CHANNEL = 5

VEVO_SEARCH_QUERIES = [
    "{artist} VEVO",
    "{artist}Vevo",
    "{artist} VEVO Official",
]

OFFICIAL_SEARCH_QUERIES = [
    "{artist} Official",
    "{artist} Official Artist Channel",
    "{artist} (Official)",
]

# ============================================================
# TITLE CLASSIFICATION — POSITIVE SIGNALS
# ============================================================

POSITIVE_TITLE_STRONG = [
    "official music video",
]

POSITIVE_TITLE_WEAK = [
    "music video",
    "official video",
]

# ============================================================
# TITLE CLASSIFICATION — HARD REJECTS
# ============================================================

NEGATIVE_TITLE_HARD = [
    # Audio-only
    "official audio",
    "audio",
    "lyrics",
    "lyric video",
    "visualizer",
    "visualiser",
    "karaoke",
    # User-generated / alternate
    "reaction",
    "cover",
    "remix",
    "shorts",
    # Promos / previews
    "trailer",
    "official trailer",
    "music video trailer",
    "teaser",
    "promo",
    "commercial",
    # Behind-the-scenes / non-MV
    "behind the scenes",
    "making of",
    "interview",
    "documentary",
    # Long-form / compilations
    "full album",
    "album stream",
    # Explicit acoustic markers
    "(acoustic)",
]

# ============================================================
# TITLE CLASSIFICATION — SOFT REJECTS
# ============================================================

NEGATIVE_TITLE_SOFT = [
    "remastered",
    "anniversary",
    "edit",
    "version",
    "radio edit",
    "clean",
    "explicit",
    "uncensored",
    "censored",
    "4k upgrade",
]

# ============================================================
# CHANNEL-LEVEL HARD BLOCKS
# ============================================================

NEGATIVE_CHANNEL_KEYWORDS = [
    "records",
    "recordings",
    "entertainment",
    "music group",
    "label",
    "archive",
    "tv",
    "media",
    "network",
    "productions",
]

# ============================================================
# DURATION HEURISTICS (SECONDS)
# ============================================================

MIN_DURATION_SEC = 120  # < 2 minutes → teaser / promo
MAX_DURATION_SEC = 450  # > 7.5 minutes → short film / compilation

# ============================================================
# DISCOVERY LIMITS
# ============================================================

MAX_ACCEPTED_PER_ARTIST = 40
FALLBACK_SEARCH_MAX_RESULTS = 10

# ============================================================
# ARTIST-SPECIFIC OVERRIDES
# ============================================================

ARTIST_MAX_VIDEO_YEAR: Dict[str, int] = {
    "Linkin Park": 2009,
}

ARTIST_IGNORE_TITLE_KEYWORDS: Dict[str, List[str]] = {
    "Korn": [
        "(from Deuce)",
    ],
}

# ============================================================
# MUSICBRAINZ CONFIGURATION
# ============================================================

MUSICBRAINZ_SEARCH_URL = "https://musicbrainz.org/ws/2/artist/"
MUSICBRAINZ_ARTIST_URL = "https://musicbrainz.org/ws/2/artist/{mbid}"
MUSICBRAINZ_RATE_LIMIT_SEC = 1.1

MB_HEADERS = {"User-Agent": "Playlistarr/1.0"}

# ============================================================
# VERSION FILTERING POLICY (REGEX-BASED)
# ============================================================

ALWAYS_ALLOWED_PHRASES = [
    "official music video",
    "official video",
    "vevo",
]

SAFE_WORDS = {
    "cover",
    "live",
    "acoustic",
    "tribute",
    "mix",
    "edit",
}

VERSION_EXCLUDE_PATTERNS = [
    # Covers
    r"\bcover(ed)?\s+by\b",
    r"\b(?:my|our|their)\s+cover\b",
    # Live
    r"\blive\s+(at|from|in)\b",
    r"\blive\s+performance\b",
    r"\blive\s+session\b",
    r"\blive\s+version\b",
    r"\(live\)",
    # Acoustic
    r"\bacoustic\s+version\b",
    r"\bacoustic\s+session\b",
    r"\(acoustic\)",
    # Remixes / edits
    r"\bremix\b",
    r"\bre[-\s]?mix\b",
    r"\bextended\s+mix\b",
    r"\bradio\s+edit\b",
    r"\bclub\s+mix\b",
    # Alternate takes
    r"\bdemo\b",
    r"\brough\s+mix\b",
    r"\balternate\s+version\b",
    # Fan / unofficial
    r"\bfan\s+made\b",
    r"\bfan\s+video\b",
    r"\bunofficial\b",
    # Low-quality reuploads
    r"\bsped\s*up\b",
    r"\bslowed\s*down\b",
    r"\bnightcore\b",
    r"\blyrics?\b",
    # Compilations
    r"\bmash\s*up\b",
    r"\bmashup\b",
    r"\bcompilation\b",
]

COMPILED_VERSION_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in VERSION_EXCLUDE_PATTERNS
]

# ============================================================
# FINAL CHANNEL TRUST BLOCKS
# ============================================================

BLOCKED_CHANNEL_KEYWORDS = [
    "lyrics",
    "lyric",
    "fan",
    "topic",
    "archive",
    "compilation",
]

# ============================================================
# PLAYLIST SYNC CONFIGURATION
# ============================================================

PLAYLIST_MUTATION_SLEEP_SEC = 1.0
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", str(6 * 60 * 60)))
YOUTUBE_BATCH_SIZE = 50


# ============================================================
# VALIDATION
# ============================================================


def validate_config() -> None:
    """Validate configuration at startup."""
    assert (
        MIN_DURATION_SEC < MAX_DURATION_SEC
    ), "MIN_DURATION_SEC must be less than MAX_DURATION_SEC"
    assert API_KEYS, "No API keys configured"
    assert len(API_KEYS) > 0, "API_KEYS list is empty"

    # Ensure directories can be created
    for directory in [AUTH_DIR, CACHE_DIR, DISCOVERY_ROOT]:
        Path(directory).mkdir(parents=True, exist_ok=True)


# Run validation on import
validate_config()
