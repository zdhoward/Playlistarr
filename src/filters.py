"""
filters.py

Pure filtering and classification helpers.

This module:
- Contains NO I/O
- Contains NO API calls
- Contains NO caching
- Contains NO state

It is safe to call anywhere and cheap to run.
All behavior is driven by config.py.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

import config


# ============================================================
# Title normalization
# ============================================================


def normalize_title(title: str) -> str:
    """
    Normalize a video title for reliable matching.

    - Lowercases
    - Collapses whitespace
    - Preserves parentheses/brackets (context matters)

    This function must be cheap and deterministic.

    Args:
        title: Video title to normalize

    Returns:
        Normalized title string
    """
    if not title:
        return ""

    t = title.lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t


def normalize_for_comparison(text: str) -> str:
    """
    Normalize text for strict comparison (removes all whitespace).

    Useful for comparing artist names against channel names where
    spacing might vary (e.g., "ArtistVEVO" vs "Artist VEVO").

    Args:
        text: Text to normalize

    Returns:
        Text with all whitespace removed, lowercased
    """
    if not text:
        return ""

    return text.lower().replace(" ", "")


# ============================================================
# Version / variant exclusion
# ============================================================


def is_excluded_version(title: str) -> Tuple[bool, Optional[str]]:
    """
    Determine whether a title represents a non-canonical version
    (live, acoustic, remix, lyrics, fan upload, etc).

    Returns:
        (is_excluded, matched_pattern)

    matched_pattern is for diagnostics only.

    Args:
        title: Video title to check

    Returns:
        Tuple of (is_excluded: bool, pattern: Optional[str])

    Examples:
        >>> is_excluded_version("Artist - Song (Official Music Video)")
        (False, None)

        >>> is_excluded_version("Artist - Song (Live at Wembley)")
        (True, '\\blive\\s+(at|from|in)\\b')
    """
    if not title:
        return False, None

    normalized = normalize_title(title)

    # --------------------------------------------------------
    # Explicit allow-list override
    # --------------------------------------------------------
    # If a title explicitly declares itself an official video,
    # we do NOT exclude it even if other patterns match.
    for phrase in config.ALWAYS_ALLOWED_PHRASES:
        if phrase in normalized:
            return False, None

    # --------------------------------------------------------
    # Regex-based exclusion patterns
    # --------------------------------------------------------
    for pattern in config.COMPILED_VERSION_PATTERNS:
        if pattern.search(normalized):
            return True, pattern.pattern

    return False, None


# ============================================================
# Channel trust evaluation
# ============================================================


def is_trusted_channel(channel_title: str, artist: str) -> bool:
    """
    Determine whether a channel is plausibly an official artist channel
    or the artist's VEVO channel.

    Rules:
    - Reject empty titles
    - Hard-reject generic impersonators (e.g., standalone "VEVO")
    - Accept artist-specific VEVO channels
    - Accept channels containing artist name

    This function is intentionally conservative.

    Args:
        channel_title: YouTube channel title
        artist: Artist name to match against

    Returns:
        True if channel is trusted, False otherwise

    Examples:
        >>> is_trusted_channel("TaylorSwiftVEVO", "Taylor Swift")
        True

        >>> is_trusted_channel("VEVO", "Taylor Swift")
        False

        >>> is_trusted_channel("Random Lyrics Channel", "Taylor Swift")
        False
    """
    if not channel_title or not artist:
        return False

    title_l = channel_title.strip().lower()
    artist_l = artist.strip().lower()

    # --------------------------------------------------------
    # Hard block: generic impersonators
    # --------------------------------------------------------
    # Prevents channels literally named "VEVO" with no artist
    if title_l == "vevo":
        return False

    # --------------------------------------------------------
    # Artist VEVO channels
    # --------------------------------------------------------
    # Normalize spacing to catch:
    #   ArtistVEVO
    #   Artist VEVO
    #   Artist   VEVO
    compact_channel = normalize_for_comparison(title_l)
    compact_artist = normalize_for_comparison(artist_l)

    if compact_channel == f"{compact_artist}vevo":
        return True

    # --------------------------------------------------------
    # Official artist channels
    # --------------------------------------------------------
    if artist_l in title_l:
        return True

    return False


# ============================================================
# Artist-specific filtering
# ============================================================


def matches_artist_ignore_keywords(artist: str, title: str) -> Optional[str]:
    """
    Check if title matches artist-specific ignore keywords.

    This allows per-artist overrides for specific problematic videos.

    Args:
        artist: Artist name
        title: Video title

    Returns:
        Matched keyword if title should be ignored, None otherwise

    Examples:
        >>> matches_artist_ignore_keywords("Korn", "Song Title (from Deuce)")
        "(from Deuce)"

        >>> matches_artist_ignore_keywords("Korn", "Regular Song Title")
        None
    """
    keywords = config.ARTIST_IGNORE_TITLE_KEYWORDS.get(artist)
    if not keywords:
        return None

    title_l = (title or "").lower()
    for keyword in keywords:
        if keyword and keyword.lower() in title_l:
            return keyword

    return None


def get_artist_year_cutoff(artist: str) -> Optional[int]:
    """
    Get the maximum allowed video year for an artist, if configured.

    Some artists have specific cutoffs (e.g., only pre-2010 videos).

    Args:
        artist: Artist name

    Returns:
        Maximum year, or None if no cutoff configured

    Examples:
        >>> get_artist_year_cutoff("Linkin Park")
        2009

        >>> get_artist_year_cutoff("Taylor Swift")
        None
    """
    return config.ARTIST_MAX_VIDEO_YEAR.get(artist)


# ============================================================
# Duration validation
# ============================================================


def is_valid_duration(duration_seconds: int) -> bool:
    """
    Check if video duration is within acceptable range.

    Args:
        duration_seconds: Video duration in seconds

    Returns:
        True if duration is valid, False otherwise

    Examples:
        >>> is_valid_duration(180)  # 3 minutes
        True

        >>> is_valid_duration(60)   # 1 minute (too short)
        False

        >>> is_valid_duration(600)  # 10 minutes (too long)
        False
    """
    return config.MIN_DURATION_SEC <= duration_seconds <= config.MAX_DURATION_SEC


# ============================================================
# Channel keyword blocking
# ============================================================


def has_blocked_channel_keyword(channel_title: str) -> Optional[str]:
    """
    Check if channel title contains any blocked keywords.

    Blocked keywords indicate label channels, archive channels,
    lyric video channels, etc.

    Args:
        channel_title: YouTube channel title

    Returns:
        Matched blocked keyword, or None if clean

    Examples:
        >>> has_blocked_channel_keyword("Sony Music Records")
        "records"

        >>> has_blocked_channel_keyword("Taylor Swift")
        None
    """
    if not channel_title:
        return None

    channel_l = channel_title.lower()

    for keyword in config.BLOCKED_CHANNEL_KEYWORDS:
        if keyword in channel_l:
            return keyword

    return None
