# 🎵 Playlistarr

[![CI](https://github.com/zdhoward/Playlistarr/actions/workflows/ci.yml/badge.svg)](https://github.com/zdhoward/Playlistarr/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A **stateful, quota-aware pipeline** for discovering, filtering, syncing, and maintaining **high-quality YouTube official music video playlists** at scale.

Built for people who care about:

* **Accuracy over volume**
* **Repeatability over one-off scripts**
* **Quota safety**
* **Long-term maintenance**
* **Managing multiple playlists independently**

This project assumes you are comfortable with Python, APIs, and structured workflows.

---

## 🚀 Quick Start

### 1. Clone and Install Dependencies

```bash
git clone <repo-url>
cd Playlistarr

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Set Up Credentials

**IMPORTANT: Never commit credentials to git**

#### YouTube API Keys (for discovery)

```bash
# Get API keys from Google Cloud Console
# Enable YouTube Data API v3
# Create multiple API keys for better quota management

export YOUTUBE_API_KEYS="AIza...key1,AIza...key2,AIza...key3"
```

#### OAuth Credentials (for playlist mutations)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create OAuth 2.0 Desktop Application
3. Download `client_secrets.json`
4. Place in `auth/client_secrets.json`

```bash
mkdir -p auth
mv ~/Downloads/client_secrets.json auth/
```

### 3. Create Artist CSV

**Important:** Name your CSV file using the pattern `{playlist_name}_artists.csv`

The playlist name (before `_artists.csv`) determines where results are stored:
- `muchloud_artists.csv` → `out/muchloud/{artist}/`
- `indie_artists.csv` → `out/indie/{artist}/`
- `hiphop_artists.csv` → `out/hiphop/{artist}/`

This lets you manage multiple playlists independently with separate artist lists.

**Example:** Create `muchloud_artists.csv`:

```csv
Artist
Taylor Swift
The Beatles
Radiohead
Billie Eilish
```

### 4. Configure Run Script

Edit `run.cmd` (Windows) or `run.sh` (Mac/Linux) to set your playlist details:

**Windows (`run.cmd`):**
```batch
set "ARTISTS_CSV=muchloud_artists.csv"
set "PLAYLIST_ID=PLxxxxxxxxxxxxxx"
```

**Mac/Linux (`run.sh`):**
```bash
ARTISTS_CSV="muchloud_artists.csv"
PLAYLIST_ID="PLxxxxxxxxxxxxxx"
```

Get your playlist ID from the YouTube URL:
```
https://www.youtube.com/playlist?list=PLa73YkAc2TvLqEb9gqMHnmjoN30qpnPe3
                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                       This is your playlist ID
```

### 5. Run the Pipeline

**Windows:**
```bash
run.cmd
```

**Mac/Linux:**
```bash
chmod +x run.sh
./run.sh
```

This single command runs the complete pipeline:
1. **Discovery** - Finds official music videos for all artists
2. **Invalidation Planning** - Identifies videos to remove
3. **Invalidation Apply** - Removes outdated videos
4. **Playlist Sync** - Adds new videos to playlist

The script will:
- Check environment setup automatically
- Run all four phases in order
- Handle quota exhaustion gracefully
- Show a summary of results
- Be resumable if interrupted

**For your first run, do a dry run:**
```bash
# Windows
run.cmd --dry-run

# Mac/Linux
./run.sh --dry-run
```

---

## 🎯 Running Individual Steps

If you need more control, you can run each phase separately:

### Discovery Only
```bash
python discover_music_videos.py muchloud_artists.csv
```

**What it does:**
- Resolves official channels for each artist (VEVO, official channels)
- Downloads video metadata from channel uploads
- Classifies videos as accepted/review/failed using semantic filters
- Saves results to `out/muchloud/{artist}/`

**Output files per artist:**
- `accepted.json` - Clean official music videos ready to sync
- `review.json` - Borderline cases that need manual review
- `failed.json` - Rejected videos with reasons
- `state.json` - Processing state for resumable discovery
- `summary.json` - Statistics and channel info

### Sync Only
```bash
python youtube_playlist_sync.py muchloud_artists.csv PLxxxxxxxxxxxxxx
```

**What it does:**
- Loads all accepted videos from `out/muchloud/{artist}/accepted.json`
- Filter version variants (live, acoustic, covers) to keep only studio versions
- Add new videos to your playlist
- Replace lower-quality duplicates with HD versions

**Options:**
```bash
# Dry run to preview changes
python youtube_playlist_sync.py muchloud_artists.csv PLxxxxxx --dry-run

# Limit additions for testing
python youtube_playlist_sync.py muchloud_artists.csv PLxxxxxx --max-add 10
```

---

## 📁 Project Structure

```
.
├── auth/                           # OAuth credentials (gitignored)
│   └── client_secrets.json        # OAuth desktop app credentials
│
├── cache/                          # Playlist caches (gitignored)
│   └── playlist_PLxxxxxx.json     # Per-playlist state/metadata
│
├── out/                            # Discovery results (gitignored)
│   ├── muchloud/                  # From muchloud_artists.csv
│   │   ├── Taylor Swift/
│   │   │   ├── accepted.json      # Videos to sync
│   │   │   ├── review.json        # Manual review needed
│   │   │   ├── failed.json        # Rejected videos
│   │   │   ├── state.json         # Processing state
│   │   │   └── summary.json       # Stats & channel info
│   │   ├── The Beatles/
│   │   └── ...
│   │
│   ├── indie/                     # From indie_artists.csv
│   │   ├── Radiohead/
│   │   └── ...
│   │
│   └── hiphop/                    # From hiphop_artists.csv
│       ├── Kendrick Lamar/
│       └── ...
│
├── config.py                       # Configuration & filter rules
├── filters.py                      # Pure filter functions
├── utils.py                        # Path & file utilities
├── api_manager.py                  # API key rotation & quota handling
├── client.py                       # OAuth client
│
├── discover_music_videos.py       # Phase 1: Discover videos
├── youtube_playlist_sync.py       # Phase 2: Sync to playlist
├── playlist_invalidate.py         # Phase 3: Generate removal plan
└── playlist_apply_invalidation.py # Phase 4: Apply removals
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Required
export YOUTUBE_API_KEYS="key1,key2,key3"

# Optional (with defaults)
export YOUTUBE_COUNTRY_CODE="CA"        # Your country for geo-blocking checks
export YT_SLEEP_SEC="0.15"              # Rate limiting between requests
export YT_REQUEST_TIMEOUT="30"          # Request timeout in seconds
export CACHE_TTL_SECONDS="21600"        # Cache TTL (6 hours)
```

### Advanced Configuration

Edit `config.py` for fine-grained control:

**Artist-specific overrides:**
```python
ARTIST_OVERRIDES = {
    "Taylor Swift": {
        "ignore_keywords": ["remix", "karaoke"],
        "year_cutoff": 2023,  # Ignore videos after this year
    }
}
```

**Duration filters:**
```python
MIN_DURATION_SEC = 120      # Minimum video length
MAX_DURATION_SEC = 600      # Maximum video length
```

**Title classification rules:**
```python
POSITIVE_TITLE_STRONG = ["official music video", "official video"]
NEGATIVE_TITLE_HARD = ["lyric video", "audio only", "visualizer"]
```

**Channel trust policies:**
```python
BLOCKED_CHANNEL_KEYWORDS = ["cover", "karaoke", "instrumental"]
MIN_UPLOADS_FOR_VIABLE_CHANNEL = 10
```

---

## 📋 Four-Phase Pipeline

### Phase 1: Discovery

```bash
python discover_music_videos.py muchloud_artists.csv
```

**What it does:**
1. For each artist in the CSV:
   - Searches for VEVO channel (highest priority)
   - Falls back to official artist channel
   - Downloads all video metadata from channel uploads
   - Classifies each video using semantic filters
   - Saves results to `out/muchloud/{artist}/`

2. Classification logic:
   - **Accept:** Official music videos from trusted channels
   - **Review:** Borderline cases (check manually)
   - **Reject:** Lyrics, covers, live versions, non-music content

3. State management:
   - Tracks processed videos in `state.json`
   - Incremental: Only processes new videos on re-run
   - Resumable: Can continue after quota exhaustion

**Quota cost:** ~5-10 units per artist (search + channel metadata + video details)

**Outputs per artist:**
- `accepted.json` - Ready to sync
- `review.json` - Need manual review
- `failed.json` - Rejected (with reasons)
- `state.json` - Processing checkpoint
- `summary.json` - Stats and channel info

**Options:**
```bash
--force-update          # Re-process all artists (ignore state)
--log-level DEBUG       # Verbose logging
```

---

### Phase 2: Playlist Sync

```bash
python youtube_playlist_sync.py muchloud_artists.csv PLxxxxxx
```

**What it does:**
1. Loads all videos from `out/muchloud/{artist}/accepted.json`
2. Fetches current playlist state (cached for 6 hours)
3. Applies additional filters:
   - Removes version variants (live, acoustic, remix, cover)
   - Removes duplicate songs (keeps best quality)
   - Removes geo-blocked videos
   - Removes unavailable videos
4. Adds new videos to playlist
5. Optionally replaces lower-quality duplicates

**Quota cost:**
- 1 unit per playlist page (list operation)
- 50 units per video added (insert operation)
- 50 units per video removed (delete operation)

**Features:**
- **Cache-backed:** Reduces API calls on repeated runs
- **Dry run mode:** Preview changes without modifying playlist
- **Rate limiting:** Respects quota limits with automatic backoff
- **Resumable:** Can continue after quota exhaustion

**Options:**
```bash
--dry-run               # Preview changes without applying
--max-add 100           # Limit number of additions
--force-update          # Ignore cache, fetch fresh playlist state
--no-filter             # Skip version variant filtering
--log-level DEBUG       # Verbose logging
```

**Example workflow:**
```bash
# 1. Dry run to preview
python youtube_playlist_sync.py muchloud_artists.csv PLxxxxxx --dry-run

# 2. Limit additions for testing
python youtube_playlist_sync.py muchloud_artists.csv PLxxxxxx --max-add 10

# 3. Full sync
python youtube_playlist_sync.py muchloud_artists.csv PLxxxxxx
```

---

### Phase 3: Generate Invalidation Plan

```bash
python playlist_invalidate.py muchloud_artists.csv PLxxxxxx
```

**What it does:**
1. Loads current playlist state from cache
2. Compares against current `accepted.json` files
3. Identifies videos to remove:
   - No longer in any artist's accepted list
   - Artist removed from CSV
   - Video reclassified as rejected
4. Generates removal plan (saved to cache)

**Quota cost:** 0 units (uses cached data)

**Output:**
- Prints list of videos to be removed
- Saves removal plan to cache for Phase 4
- No API calls made

**Important:** This is a **planning** phase only. No videos are actually removed.

---

### Phase 4: Apply Removals

```bash
python playlist_apply_invalidation.py PLxxxxxx
```

**What it does:**
1. Loads removal plan from cache (generated in Phase 3)
2. Removes each video from playlist
3. Updates cache after each removal
4. Handles quota exhaustion gracefully

**Quota cost:** 50 units per video removed

**Features:**
- Resumable: Tracks progress, can continue after quota exhaustion
- Atomic: Updates cache after each successful removal
- Safe: Requires Phase 3 plan to exist

**Options:**
```bash
--log-level DEBUG       # Verbose logging
```

---

## 📝 Common Workflows

### Initial Setup (New Playlist)

**Simple way (recommended):**

```bash
# 1. Create your artist CSV with descriptive name
cat > muchloud_artists.csv << EOF
Artist
Taylor Swift
The Beatles
Radiohead
Billie Eilish
EOF

# 2. Edit run.cmd (Windows) or run.sh (Mac/Linux) with your playlist ID
#    Set ARTISTS_CSV=muchloud_artists.csv
#    Set PLAYLIST_ID=PLxxxxxxxxxxxxxx

# 3. Do a dry run to preview changes
# Windows:
run.cmd --dry-run

# Mac/Linux:
./run.sh --dry-run

# 4. Run the full pipeline
# Windows:
run.cmd

# Mac/Linux:
./run.sh
```

**Manual way (more control):**

```bash
# 1. Create your artist CSV with descriptive name
cat > muchloud_artists.csv << EOF
Artist
Taylor Swift
The Beatles
Radiohead
Billie Eilish
EOF

# 2. Discover videos for all artists
python discover_music_videos.py muchloud_artists.csv

# 3. Review discovery results
cat out/muchloud/Taylor\ Swift/summary.json | jq

# 4. Check what will be synced (dry run)
python youtube_playlist_sync.py muchloud_artists.csv PLxxxxxx --dry-run

# 5. Sync to playlist (start small for testing)
python youtube_playlist_sync.py muchloud_artists.csv PLxxxxxx --max-add 20

# 6. Full sync
python youtube_playlist_sync.py muchloud_artists.csv PLxxxxxx
```

---

### Managing Multiple Playlists

The `{playlist_name}_artists.csv` naming pattern lets you manage multiple playlists independently.

**Option 1: Create separate run scripts**

Copy and customize the run script for each playlist:

```bash
# Windows
copy run.cmd run_indie.cmd
copy run.cmd run_hiphop.cmd

# Mac/Linux
cp run.sh run_indie.sh
cp run.sh run_hiphop.sh
chmod +x run_indie.sh run_hiphop.sh
```

Edit each script with different settings:

**`run_indie.cmd`:**
```batch
set "ARTISTS_CSV=indie_artists.csv"
set "PLAYLIST_ID=PLindiePlaylistID"
```

**`run_hiphop.cmd`:**
```batch
set "ARTISTS_CSV=hiphop_artists.csv"
set "PLAYLIST_ID=PLhiphopPlaylistID"
```

Then run each independently:
```bash
# Windows
run_indie.cmd
run_hiphop.cmd

# Mac/Linux
./run_indie.sh
./run_hiphop.sh
```

**Option 2: Run individual commands**

```bash
# Create separate CSVs for different playlists
cat > indie_artists.csv << EOF
Artist
Radiohead
Arcade Fire
LCD Soundsystem
Modest Mouse
EOF

cat > hiphop_artists.csv << EOF
Artist
Kendrick Lamar
Drake
Travis Scott
J. Cole
EOF

# Discover for each playlist (results stored separately)
python discover_music_videos.py indie_artists.csv    # → out/indie/
python discover_music_videos.py hiphop_artists.csv   # → out/hiphop/

# Sync to different playlists
python youtube_playlist_sync.py indie_artists.csv PLindiePlaylistID
python youtube_playlist_sync.py hiphop_artists.csv PLhiphopPlaylistID

# Each playlist has independent:
# - Discovery results (out/indie/ vs out/hiphop/)
# - Playlist cache (cache/playlist_PLindiePlaylistID.json)
# - Processing state (state.json per artist)
```

---

### Regular Maintenance

Run the pipeline weekly/monthly to keep playlists updated:

**Simple way (recommended):**
```bash
# Windows
run.cmd

# Mac/Linux
./run.sh
```

This runs all four phases automatically and handles quota exhaustion gracefully.

**Manual way (more control):**
```bash
# 1. Discover new videos (incremental, only checks new uploads)
python discover_music_videos.py muchloud_artists.csv

# 2. Sync new videos to playlist (limit additions for safety)
python youtube_playlist_sync.py muchloud_artists.csv PLxxxxxx --max-add 50

# 3. Identify videos to remove (no API calls)
python playlist_invalidate.py muchloud_artists.csv PLxxxxxx

# 4. Apply removals
python playlist_apply_invalidation.py PLxxxxxx
```

---

### Adding New Artists

```bash
# 1. Add artist to existing CSV
echo "Dua Lipa" >> muchloud_artists.csv

# 2. Discover (only processes new artist due to state tracking)
python discover_music_videos.py muchloud_artists.csv

# 3. Review results
cat out/muchloud/Dua\ Lipa/summary.json | jq

# 4. Sync new artist's videos
python youtube_playlist_sync.py muchloud_artists.csv PLxxxxxx
```

---

### Removing Artists

```bash
# 1. Remove artist from CSV (edit muchloud_artists.csv)

# 2. Generate removal plan (identifies removed artist's videos)
python playlist_invalidate.py muchloud_artists.csv PLxxxxxx

# 3. Apply removals
python playlist_apply_invalidation.py PLxxxxxx

# 4. Optionally clean up discovery results
rm -rf out/muchloud/Artist\ Name/
```

---

### Force Refresh

When you want to re-process everything from scratch:

```bash
# Re-discover all artists (ignores state.json)
python discover_music_videos.py muchloud_artists.csv --force-update

# Re-fetch playlist state (ignores cache)
python youtube_playlist_sync.py muchloud_artists.csv PLxxxxxx --force-update
```

---

### Handling Quota Exhaustion

When you hit quota limits (resets daily at midnight Pacific Time):

```bash
# Discovery exhausted - just run again tomorrow
python discover_music_videos.py muchloud_artists.csv
# Picks up where it left off automatically

# Sync exhausted - run again tomorrow
python youtube_playlist_sync.py muchloud_artists.csv PLxxxxxx
# Cached state prevents re-processing

# Apply removals exhausted - run again tomorrow
python playlist_apply_invalidation.py PLxxxxxx
# Tracks progress, continues from last successful removal
```

**To avoid quota issues:**
1. Use multiple API keys (comma-separated in `YOUTUBE_API_KEYS`)
2. Limit operations with `--max-add`
3. Run during off-peak hours
4. Split large artist lists into multiple CSVs

---

## 📊 Monitoring & Debugging

### Check Discovery Status

```bash
# Summary for all artists in a playlist
for dir in out/muchloud/*/; do
    artist=$(basename "$dir")
    echo "=== $artist ==="
    cat "$dir/summary.json" | jq '{channel: .channel.channel_title, accepted, review, failed}'
done

# Count total videos discovered
echo "Total accepted:" $(cat out/muchloud/*/accepted.json | jq length | awk '{s+=$1} END {print s}')

# Find artists with no channel found
grep -l '"channel": null' out/muchloud/*/summary.json
```

### Review Borderline Videos

```bash
# List videos needing manual review
cat out/muchloud/Taylor\ Swift/review.json | jq '.[] | {title, reason, url}'

# After manual review, move to accepted or failed:
# Edit accepted.json and failed.json manually
```

### Check Playlist State

```bash
# View cached playlist info
cat cache/playlist_PLxxxxxx.json | jq '{
    total_items: (.items_by_video_id | length),
    last_updated,
    playlist_title
}'

# List all videos in playlist
cat cache/playlist_PLxxxxxx.json | jq -r '.items_by_video_id | to_entries[] | .value.title'

# Find duplicate videos
cat cache/playlist_PLxxxxxx.json | jq -r '.items_by_video_id | to_entries[] | .value.title' | sort | uniq -d
```

### Debug Failed Discovery

```bash
# Run with debug logging
python discover_music_videos.py muchloud_artists.csv --log-level DEBUG

# Check why specific artist failed
cat out/muchloud/Some\ Artist/summary.json | jq

# Common issues:
# - "matched_via": "none" → Artist channel not found
# - accepted: 0 → No videos passed filters
# - Look in failed.json for rejection reasons
```

### Verify Sync Results

```bash
# Dry run shows what will change
python youtube_playlist_sync.py muchloud_artists.csv PLxxxxxx --dry-run

# Compare before/after
ls -lh cache/playlist_PLxxxxxx.json  # Check modification time
```

---

## 🛡️ Safety Features

### Quota Management

- **Multi-key rotation**: Automatically cycles through multiple API keys
- **Graceful degradation**: Stops cleanly when quota exhausted
- **Quota detection**: Recognizes 403 quota errors and handles appropriately
- **Resumable operations**: All phases can pick up where they left off

### State Tracking

- **Incremental discovery**: Only processes new/changed videos
- **Cache-backed sync**: Reduces redundant API calls
- **Atomic operations**: Updates state after each successful operation
- **Progress logging**: Always know current status

### Error Handling

- **Retry with exponential backoff**: Handles transient network errors
- **Type-safe errors**: `QuotaExhaustedError` vs generic exceptions
- **Detailed logging**: Full context for debugging
- **Validation**: Checks for required files and configurations

### Data Integrity

- **No silent failures**: All errors logged with context
- **Backup-friendly**: JSON outputs are human-readable
- **Idempotent**: Safe to run multiple times
- **Dry-run mode**: Preview changes before applying

---

## 🛠️ Troubleshooting

### "Quota Exhausted"

**Symptom:** Script stops with `QuotaExhaustedError`

**Solution:**
1. Wait until midnight Pacific Time (quota resets daily)
2. Add more API keys:
   ```bash
   export YOUTUBE_API_KEYS="$YOUTUBE_API_KEYS,new_key_here"
   ```
3. Run again - script picks up where it left off

---

### "Invalid Playlist ID"

**Symptom:** Error about playlist not found or access denied

**Solution:**
1. Verify playlist ID format:
   ```
   https://www.youtube.com/playlist?list=PLxxxxxxxxxxxxxx
                                         ^^^ This part (starts with PL)
   ```
2. Ensure playlist is owned by OAuth account
3. Check OAuth permissions include YouTube management scope
4. Re-run OAuth flow: `rm auth/credentials.json` and sync again

---

### "Artist Not Found / No Channel"

**Symptom:** `summary.json` shows `"matched_via": "none"` and `"channel": null`

**Solution:**
1. Manually search YouTube for artist's official channel
2. Get channel ID from URL:
   ```
   https://www.youtube.com/channel/UCxxxxxxxxxxxxxx
                                   ^^^ Channel ID
   ```
3. Add manual override in `config.py`:
   ```python
   ARTIST_OVERRIDES = {
       "Artist Name": {
           "channel_id": "UCxxxxxxxxxxxxxx"
       }
   }
   ```
4. Re-run with `--force-update`

---

### "No Videos Accepted"

**Symptom:** Discovery finds channel but `accepted.json` is empty

**Solution:**
1. Check `failed.json` for rejection reasons:
   ```bash
   cat out/muchloud/Artist/failed.json | jq '[.[] | .reason] | group_by(.) | map({reason: .[0], count: length})'
   ```
2. Common reasons:
   - `not_music_video`: Videos lack "official music video" in title
   - `too_short` / `too_long`: Duration filters
   - `year_cutoff`: Videos too new/old
   - `score=-2`: Semantic filters rejected

3. Adjust filters in `config.py` if needed:
   ```python
   MIN_DURATION_SEC = 90  # Lower minimum
   MAX_DURATION_SEC = 900  # Raise maximum
   ```

---

### "Cache Corrupted / Stale"

**Symptom:** Sync behaves unexpectedly or shows outdated data

**Solution:**
```bash
# Delete cache and refresh
rm cache/playlist_PLxxxxxx.json
python youtube_playlist_sync.py muchloud_artists.csv PLxxxxxx --force-update
```

---

### "Permission Denied" on OAuth

**Symptom:** OAuth flow fails or can't modify playlist

**Solution:**
1. Ensure `auth/client_secrets.json` is correct OAuth Desktop App credentials
2. Delete old credentials: `rm auth/credentials.json`
3. Re-run sync to trigger fresh OAuth flow
4. When browser opens, sign in with account that owns the playlist
5. Grant all requested permissions

---

### "Too Many Duplicates in Playlist"

**Symptom:** Multiple versions of same song added

**Solution:**
1. Version filtering is enabled by default, but you can verify:
   ```bash
   # Check if filtering is working
   python youtube_playlist_sync.py muchloud_artists.csv PLxxxxxx --dry-run | grep -i "filtered"
   ```
2. Manually clean up existing duplicates:
   ```bash
   # Generate removal plan for duplicates
   python playlist_invalidate.py muchloud_artists.csv PLxxxxxx
   python playlist_apply_invalidation.py PLxxxxxx
   ```
3. Adjust duplicate detection in `config.py` if needed

---

## 🔒 Security Best Practices

### Credential Safety

1. **Never commit credentials to version control**
   ```bash
   # Verify gitignore
   git check-ignore auth/client_secrets.json  # Should show: auth/client_secrets.json
   git check-ignore auth/credentials.json     # Should show: auth/credentials.json
   ```

2. **Use environment variables for API keys**
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   export YOUTUBE_API_KEYS="key1,key2,key3"
   ```

3. **Rotate API keys periodically**
   - Generate new keys every 90 days
   - Disable old keys in Google Cloud Console
   - Update environment variable

4. **Restrict OAuth scope**
   - Only grant YouTube management scope
   - Revoke access when not in use
   - Review authorized apps: https://myaccount.google.com/permissions

### API Key Protection

1. **Restrict API keys in Google Cloud Console**
   - Add HTTP referrer restrictions (if applicable)
   - Restrict to YouTube Data API v3 only
   - Enable API key usage monitoring

2. **Monitor quota usage**
   - Check Google Cloud Console daily usage
   - Set up quota alerts
   - Use `--max-add` to control quota burn

3. **Separate keys by environment**
   ```bash
   # Development
   export YOUTUBE_API_KEYS="dev_key1,dev_key2"
   
   # Production
   export YOUTUBE_API_KEYS="prod_key1,prod_key2,prod_key3"
   ```

---

## 🧪 Development

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test
pytest tests/test_filters.py -v
```

### Code Quality

```bash
# Format code
black *.py

# Type checking
mypy *.py --ignore-missing-imports

# Linting
flake8 *.py --max-line-length=100

# All checks (what CI runs)
black --check *.py
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
mypy *.py --ignore-missing-imports
```

### Adding Features

1. **Pure logic** → `filters.py`
   - No side effects
   - Easy to test
   - Example: Title classification, duration checks

2. **API interactions** → `api_manager.py` or script files
   - Quota-aware
   - Error handling
   - Retry logic

3. **Configuration** → `config.py`
   - Constants
   - Artist overrides
   - Filter thresholds

4. **Update tests** → `tests/`
   - Add test cases
   - Ensure coverage
   - Run before committing

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest tests/`)
6. Run code quality checks (`black`, `flake8`, `mypy`)
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

---

## 📄 License

MIT License - see LICENSE file for details

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/zdhoward/Playlistarr/issues)
- **Discussions**: [GitHub Discussions](https://github.com/zdhoward/Playlistarr/discussions)
- **Documentation**: This README