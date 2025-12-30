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
- Reading environment variables
- Validation / side effects

Runtime configuration (env vars, profiles) belongs in:
- env.py
- playlistarr.py (CLI bootstrap)
- runner.py (orchestration)
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List
from env import PROJECT_ROOT

# ============================================================
# PROJECT PATHS
# ============================================================

AUTH_DIR = PROJECT_ROOT / "auth"
CACHE_DIR = PROJECT_ROOT / "cache"
DISCOVERY_ROOT = PROJECT_ROOT / "out"
LOG_DIR = PROJECT_ROOT / "logs"
PROFILES_DIR = PROJECT_ROOT / "profiles"

CLIENT_SECRETS_FILE = AUTH_DIR / "client_secrets.json"
OAUTH_TOKEN_FILE = AUTH_DIR / "oauth_token.json"
# Playlist cache / plans (actual filenames are generated elsewhere)
PLAYLIST_CACHE_BASENAME = "playlist_{playlist_id}.json"
INVALIDATION_PLAN_BASENAME = "invalidation_{playlist_id}.json"

SLEEP_BETWEEN_CALLS_SEC = float(os.environ.get("YT_SLEEP_SEC", "0.15"))
REQUEST_TIMEOUT = int(os.environ.get("YT_REQUEST_TIMEOUT", "30"))
MAX_RETRIES = int(os.environ.get("YT_MAX_RETRIES", "3"))
BACKOFF_BASE_SEC = float(os.environ.get("YT_BACKOFF_BASE_SEC", "1.0"))

# ============================================================
# YOUTUBE API — ENDPOINTS / SCOPES
# ============================================================

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"

YOUTUBE_OAUTH_SCOPES = ["https://www.googleapis.com/auth/youtube"]

# Defaults only. env.py may override.
DEFAULT_COUNTRY_CODE = "CA"

# ============================================================
# REQUEST THROTTLING DEFAULTS (env.py may override)
# ============================================================

DEFAULT_SLEEP_BETWEEN_CALLS_SEC = 0.15
DEFAULT_REQUEST_TIMEOUT_SEC = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE_SEC = 1.0

# Playlist mutations are intentionally slower (env.py/profile may override)
DEFAULT_PLAYLIST_MUTATION_SLEEP_SEC = 1.0

# Cache TTL default: 6 hours
DEFAULT_CACHE_TTL_SECONDS = 6 * 60 * 60

# YouTube API max page size for playlistItems.list is 50
YOUTUBE_BATCH_SIZE = 50

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
    # Explicit acoustic markers / special cases
    "(acoustic)",
    "(manga series)",
    "(avril commentary)",
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
# ARTIST-SPECIFIC OVERRIDES (defaults; profiles may override)
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
MUSICBRAINZ_RATE_LIMIT_SEC = 2
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
# LOGGING DEFAULTS (logger.py/env.py control actual behavior)
# ============================================================

DEFAULT_LOG_DIR = "../logs"
DEFAULT_LOG_RETENTION = 10
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "text"
