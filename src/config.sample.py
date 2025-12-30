"""
config.sample.py

SAMPLE configuration file for Playlistarr.

⚠️  DO NOT USE THIS FILE DIRECTLY ⚠️

This is a reference showing what configuration options are available.
The actual config.py loads values from environment variables.

To use this project:
1. Set environment variables (see .env.example)
2. Copy this file to understand available options
3. Modify config.py if you need custom logic

NEVER commit real API keys or secrets!
"""

# ============================================================
# ENVIRONMENT VARIABLES (Set these in your shell or .env)
# ============================================================

# Required:
# export YOUTUBE_API_KEYS="API_KEY_1,API_KEY_2,API_KEY_3,..."

# Optional (with defaults):
# export YOUTUBE_COUNTRY_CODE="US"              # Default: CA
# export YT_SLEEP_SEC="0.15"                    # Default: 0.15
# export YT_REQUEST_TIMEOUT="30"                # Default: 30
# export YT_MAX_RETRIES="3"                     # Default: 3
# export YT_BACKOFF_BASE_SEC="1.0"              # Default: 1.0
# export CACHE_TTL_SECONDS="21600"              # Default: 21600 (6 hours)

# ============================================================
# FILESYSTEM PATHS
# ============================================================

AUTH_DIR = "../auth"  # OAuth credentials directory
CACHE_DIR = "../cache"  # Playlist caches
DISCOVERY_ROOT = "out"  # Discovery output

CLIENT_SECRETS_FILE = "../auth/client_secrets.json"  # OAuth client secrets
OAUTH_TOKEN_FILE = "../auth/oauth_token.json"  # OAuth token (auto-generated)

# ============================================================
# API CONFIGURATION
# ============================================================

# YouTube API endpoints (should not need to change)
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"

# OAuth scopes
YOUTUBE_OAUTH_SCOPES = ["https://www.googleapis.com/auth/youtube"]

# API safety settings
SLEEP_BETWEEN_CALLS_SEC = 0.15  # Rate limiting between API calls
REQUEST_TIMEOUT = 30  # HTTP timeout in seconds
MAX_RETRIES = 3  # Max retry attempts for failed requests
BACKOFF_BASE_SEC = 1.0  # Exponential backoff base

# ============================================================
# DISCOVERY SETTINGS
# ============================================================

# Channel resolution
MIN_UPLOADS_FOR_VIABLE_CHANNEL = 5  # Minimum videos for valid channel

# VEVO search queries (in order of preference)
VEVO_SEARCH_QUERIES = [
    "{artist} VEVO",
    "{artist}Vevo",
    "{artist} VEVO Official",
]

# Official channel search queries (fallback)
OFFICIAL_SEARCH_QUERIES = [
    "{artist} Official",
    "{artist} Official Artist Channel",
    "{artist} (Official)",
]

# ============================================================
# VIDEO CLASSIFICATION RULES
# ============================================================

# Positive signals (indicates official music video)
POSITIVE_TITLE_STRONG = [
    "official music video",
]

POSITIVE_TITLE_WEAK = [
    "music video",
    "official video",
]

# Hard rejects (immediate disqualification)
NEGATIVE_TITLE_HARD = [
    # Audio-only
    "official audio",
    "audio",
    "lyrics",
    "lyric video",
    "visualizer",
    "visualiser",
    "karaoke",
    # User-generated content
    "reaction",
    "cover",
    "remix",
    "shorts",
    # Promotional content
    "trailer",
    "official trailer",
    "teaser",
    "promo",
    "commercial",
    # Behind-the-scenes
    "behind the scenes",
    "making of",
    "interview",
    "documentary",
    # Long-form content
    "full album",
    "album stream",
    # Acoustic versions
    "(acoustic)",
]

# Soft rejects (scored lower but not auto-rejected)
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

# Channel-level blocks
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
# DURATION FILTERS (seconds)
# ============================================================

MIN_DURATION_SEC = 120  # 2 minutes - shorter = likely teaser/promo
MAX_DURATION_SEC = 450  # 7.5 minutes - longer = short film/compilation

# ============================================================
# DISCOVERY LIMITS
# ============================================================

MAX_ACCEPTED_PER_ARTIST = 40  # Max videos to accept per artist
FALLBACK_SEARCH_MAX_RESULTS = 10  # Max results for fallback search

# ============================================================
# ARTIST-SPECIFIC OVERRIDES
# ============================================================

# Limit videos by year (e.g., band member changes)
ARTIST_MAX_VIDEO_YEAR = {
    "Linkin Park": 2009,  # Before lineup changes
    # Add more as needed:
    # "Artist Name": 2015,
}

# Artist-specific title keyword blocks
ARTIST_IGNORE_TITLE_KEYWORDS = {
    "Korn": [
        "(from Deuce)",  # Compilation releases
    ],
    # Add more as needed:
    # "Artist Name": ["keyword1", "keyword2"],
}

# ============================================================
# VERSION FILTERING
# ============================================================

# Always allow these phrases (even if they match version patterns)
ALWAYS_ALLOWED_PHRASES = [
    "official music video",
    "official video",
    "vevo",
]

# Detect and filter these version types
SAFE_WORDS = {
    "cover",
    "live",
    "acoustic",
    "tribute",
    "mix",
    "edit",
}

# Regex patterns for version detection
VERSION_EXCLUDE_PATTERNS = [
    r"\bcover(ed)?\s+by\b",
    r"\blive\s+(at|from|in)\b",
    r"\bacoustic\s+version\b",
    r"\bremix\b",
    r"\bdemo\b",
    r"\bfan\s+made\b",
    r"\bsped\s*up\b",
    r"\bmash\s*up\b",
    # Add more patterns as needed
]

# ============================================================
# CHANNEL TRUST
# ============================================================

# Block channels with these keywords
BLOCKED_CHANNEL_KEYWORDS = [
    "lyrics",
    "lyric",
    "fan",
    "topic",
    "archive",
    "compilation",
]

# ============================================================
# PLAYLIST SYNC
# ============================================================

PLAYLIST_MUTATION_SLEEP_SEC = 1.0  # Sleep after playlist modifications
CACHE_TTL_SECONDS = 21600  # 6 hours cache TTL
YOUTUBE_BATCH_SIZE = 50  # Batch size for API requests

# ============================================================
# MUSICBRAINZ INTEGRATION (Future)
# ============================================================

MUSICBRAINZ_SEARCH_URL = "https://musicbrainz.org/ws/2/artist/"
MUSICBRAINZ_ARTIST_URL = "https://musicbrainz.org/ws/2/artist/{mbid}"
MUSICBRAINZ_RATE_LIMIT_SEC = 1.1  # MusicBrainz requires 1 req/sec

MB_HEADERS = {"User-Agent": "Playlistarr/1.0"}

# ============================================================
# CUSTOMIZATION EXAMPLES
# ============================================================

# Example 1: Stricter duration filtering
# MIN_DURATION_SEC = 150    # 2.5 minutes minimum
# MAX_DURATION_SEC = 360    # 6 minutes maximum

# Example 2: More aggressive version filtering
# Add to VERSION_EXCLUDE_PATTERNS:
# r"\b\d{4}\s+version\b",   # Year versions
# r"\bremaster(ed)?\b",     # Remasters

# Example 3: Artist-specific channel preference
# ARTIST_CHANNEL_PREFERENCE = {
#     "Taylor Swift": "TaylorSwiftVEVO",
#     "Ed Sheeran": "EdSheeran",  # Prefer non-VEVO
# }

# Example 4: Custom positive signals
# POSITIVE_TITLE_STRONG += [
#     "music film",           # For artists who make short films
#     "official visual",      # Alternative terminology
# ]

# Example 5: Genre-specific filters
# GENRE_FILTERS = {
#     "electronic": {
#         "min_duration": 180,    # Electronic tracks are longer
#         "max_duration": 600,
#     },
#     "punk": {
#         "min_duration": 90,     # Punk songs are shorter
#         "max_duration": 300,
#     },
# }

# ============================================================
# NOTES FOR CUSTOMIZATION
# ============================================================

"""
Tips for customizing this configuration:

1. Start with defaults and adjust based on results
2. Check rejected.json files to tune filters
3. Add artist-specific overrides sparingly
4. Test changes with a small artist list first
5. Document why you changed defaults (for future you)

Common customizations:
- Adjust MIN_DURATION_SEC if getting too many short videos
- Add to NEGATIVE_TITLE_HARD for specific unwanted content
- Use ARTIST_MAX_VIDEO_YEAR for bands with lineup changes
- Modify VERSION_EXCLUDE_PATTERNS for your specific needs

Remember:
- This is a SAMPLE file showing structure
- Real config.py loads from environment variables
- Never commit API keys or secrets!
- Test configuration changes before full discovery
"""
