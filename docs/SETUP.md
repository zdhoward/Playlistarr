# Complete Setup Guide

This guide walks you through setting up Playlistarr from scratch.

---

## Prerequisites

- Python 3.8 or higher
- Google Cloud account
- YouTube account with playlist creation permissions
- Basic command-line knowledge

---

## Step 1: Google Cloud Setup

### 1.1 Create Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click "Select a project" → "New Project"
3. Name: "Playlistarr"
4. Click "Create"

### 1.2 Enable YouTube Data API

1. In Cloud Console, go to "APIs & Services" → "Library"
2. Search for "YouTube Data API v3"
3. Click "Enable"

### 1.3 Create API Keys (for Discovery)

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "API Key"
3. **Restrict the key:**
   - Click "Edit API key"
   - Under "API restrictions", select "Restrict key"
   - Choose "YouTube Data API v3"
   - Save
4. **Copy the key** (looks like `AIzaSy...`)
5. **Repeat 3-5 times** to create multiple keys for better quota

**Why multiple keys?**
- Each key has 10,000 quota units per day
- Discovery uses ~5-10 units per artist
- Multiple keys = more quota

### 1.4 Create OAuth Credentials (for Playlist Management)

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure consent screen:
   - User Type: External
   - App name: "Playlistarr"
   - User support email: your email
   - Developer contact: your email
   - Scopes: Add `../auth/youtube` (YouTube management)
   - Test users: Add your email
   - Save
4. Back to "Create OAuth client ID":
   - Application type: **Desktop app**
   - Name: "Playlistarr Desktop"
   - Click "Create"
5. **Download JSON** → Save as `client_secrets.json`

---

## Step 2: Project Setup

### 2.1 Install Python Dependencies

```bash
# Clone or download the project
cd Playlistarr

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2.2 Set Up Directory Structure

```bash
# Create required directories
mkdir -p auth cache out

# Move OAuth credentials
mv ~/Downloads/client_secrets.json auth/

# Verify structure
ls -la auth/
# Should show: client_secrets.json
```

### 2.3 Configure Environment Variables

**Option A: Shell Export (Temporary)**

```bash
export YOUTUBE_API_KEYS="API_KEY_1,API_KEY_2,API_KEY_3,..."
export YOUTUBE_COUNTRY_CODE="US"  # Optional, default is CA
```

**Option B: .env File (Recommended)**

Create `.env` in project root:

```bash
# .env
YOUTUBE_API_KEYS=API_KEY_1,API_KEY_2,API_KEY_3,...
YOUTUBE_COUNTRY_CODE=US
YT_SLEEP_SEC=0.15
CACHE_TTL_SECONDS=21600
```

Then load it:

```bash
# Install python-dotenv
pip install python-dotenv

# Add to your scripts:
from dotenv import load_dotenv
load_dotenv()
```

**Option C: Shell Config (Permanent)**

Add to `~/.bashrc` or `~/.zshrc`:

```bash
export YOUTUBE_API_KEYS="API_KEY_1,API_KEY_2,API_KEY_3,..."
export YOUTUBE_COUNTRY_CODE="US"
```

Then:

```bash
source ~/.bashrc  # or ~/.zshrc
```

### 2.4 Verify Configuration

```bash
python -c "import config; print(f'Loaded {len(config.API_KEYS)} API keys')"
# Should output: Loaded 3 API keys (or however many you have)
```

---

## Step 3: Create Artist List

Create `artists.csv`:

```csv
Artist
Taylor Swift
The Beatles
Radiohead
Linkin Park
Foo Fighters
```

**Tips:**
- One artist per line
- Use exact artist names (as they appear on YouTube)
- Start with 5-10 artists for testing
- Remove "Artist" header if it causes issues

---

## Step 4: Test Discovery

### 4.1 Run Discovery (Dry Run)

```bash
python discover_music_videos.py artists.csv --log-level DEBUG
```

**What to expect:**
- "Resolving channel for {artist}..."
- "Found channel: {channel_name}"
- "Processing videos..."
- "Accepted: X, Review: Y, Failed: Z"

**Troubleshooting:**

If you see:
```
ValueError: YOUTUBE_API_KEYS environment variable not set
```
→ Set environment variables (Step 2.3)

If you see:
```
FileNotFoundError: Missing OAuth client secrets file
```
→ Move `client_secrets.json` to `auth/` directory

If you see:
```
403 Quota exhausted
```
→ Wait 24 hours or add more API keys

### 4.2 Check Output

```bash
# List discovered artists
ls out/artists/

# Check one artist's results
cat out/artists/Taylor\ Swift/summary.json | jq .
```

Expected output:
```json
{
  "artist": "Taylor Swift",
  "channel": {
    "channel_id": "UCqECaJ8Gagnn7YCbPEzWH6g",
    "channel_title": "TaylorSwiftVEVO",
    "is_vevo": true
  },
  "matched_via": "vevo_search",
  "accepted": 42,
  "review": 5,
  "failed": 18
}
```

---

## Step 5: Create YouTube Playlist

### 5.1 Create Playlist

1. Go to [YouTube](https://youtube.com)
2. Click your profile → "Your channel"
3. Click "Playlists" → "New playlist"
4. Name: "Music Videos Collection"
5. Privacy: Public/Unlisted/Private
6. Click "Create"

### 5.2 Get Playlist ID

The playlist URL looks like:
```
https://www.youtube.com/playlist?list=PLxxxxxxxxxxxxxxxxxxxxxx
                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^
                                      This is your playlist ID
```

Copy the ID (starts with `PL`)

---

## Step 6: Test Playlist Sync

### 6.1 Dry Run

```bash
python youtube_playlist_sync.py artists.csv PLxxxxxxxxxxxxxx --dry-run
```

**What to expect:**
- "Loading candidates from out/artists..."
- "Candidates: X (best-per-song_key after filtering)"
- "[DRY-RUN] Additions:" followed by list of videos
- No actual playlist changes

### 6.2 Authenticate OAuth

When you run sync **without** `--dry-run`, you'll see:

```
Please visit this URL to authorize this application:
https://accounts.google.com/o/oauth2/auth?...
```

1. Click the URL (or copy-paste to browser)
2. Log in to your Google account
3. Click "Allow" to grant permissions
4. Browser will show "The authentication flow has completed"
5. Return to terminal

**First time only** - credentials are saved to `auth/oauth_token.json`

### 6.3 Actual Sync (Limited)

```bash
python youtube_playlist_sync.py artists.csv PLxxxxxxxxxxxxxx --max-add 10
```

This adds **maximum 10 videos** to test everything works.

**What to expect:**
- "Executing additions..."
- "Added {video_id} (playlistItemId=...) song_key=..."
- Progress updates

### 6.4 Verify in YouTube

1. Go to your playlist URL
2. You should see 10 videos added
3. Check they're official music videos

---

## Step 7: Full Sync

Once testing is complete:

```bash
# Sync all accepted videos
python youtube_playlist_sync.py artists.csv PLxxxxxxxxxxxxxx

# Or limit to avoid quota issues
python youtube_playlist_sync.py artists.csv PLxxxxxxxxxxxxxx --max-add 200
```

**Quota usage:**
- 50 units per video added
- With 10,000 units/day, you can add ~200 videos/day
- Use `--max-add` to control quota consumption

---

## Step 8: Maintenance Setup

### 8.1 Discover New Videos (Weekly)

```bash
# Incremental discovery (only new videos)
python discover_music_videos.py artists.csv

# Sync new additions
python youtube_playlist_sync.py artists.csv PLxxxxxxxxxxxxxx --max-add 50
```

### 8.2 Remove Invalid Videos (Monthly)

```bash
# Generate removal plan
python playlist_invalidate.py artists.csv PLxxxxxxxxxxxxxx

# Review plan
cat cache/invalidation_PLxxxxxxxxxxxxxx.json | jq '.actions | length'

# Apply removals
python playlist_apply_invalidation.py PLxxxxxxxxxxxxxx
```

### 8.3 Automate with Cron (Linux/Mac)

Create `run_maintenance.sh`:

```bash
#!/bin/bash
cd /path/to/Playlistarr
source venv/bin/activate
source .env  # If using .env file

# Discovery
python discover_music_videos.py artists.csv >> logs/discovery.log 2>&1

# Sync (limited)
python youtube_playlist_sync.py artists.csv PLxxxxxx --max-add 50 >> logs/sync.log 2>&1
```

Make executable:
```bash
chmod +x run_maintenance.sh
```

Add to crontab:
```bash
crontab -e

# Add this line (runs every Sunday at 2 AM):
0 2 * * 0 /path/to/Playlistarr/run_maintenance.sh
```

---

## Step 9: Monitoring

### 9.1 Check Discovery Status

```bash
# List all artists
ls out/artists/

# Show summary for all artists
for dir in out/artists/*/; do
    artist=$(basename "$dir")
    echo "=== $artist ==="
    cat "$dir/summary.json" | jq '{accepted, review, failed}'
done
```

### 9.2 Check Quota Usage

Google Cloud Console → APIs & Services → Dashboard

- View requests per day
- Check quota remaining
- Set up alerts

### 9.3 View Logs

```bash
# Run with debug output
python discover_music_videos.py artists.csv --log-level DEBUG

# Save to file
python discover_music_videos.py artists.csv 2>&1 | tee logs/discovery.log
```

---

## Common Issues & Solutions

### Issue: "ModuleNotFoundError: No module named 'google'"

**Solution:**
```bash
# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "403 Quota Exceeded"

**Solution:**
- Wait 24 hours (quota resets midnight Pacific Time)
- Add more API keys
- Use `--max-add` to limit operations

### Issue: "401 Unauthorized" during OAuth

**Solution:**
```bash
# Delete cached token
rm auth/oauth_token.json

# Re-authenticate
python youtube_playlist_sync.py artists.csv PLxxxxxx
```

### Issue: Artist channel not found

**Solution:**
1. Check artist name spelling
2. Manually search YouTube for official channel
3. Add channel URL to discovery output
4. Or skip artist

### Issue: Too many low-quality videos

**Solution:**
Edit `config.py` filters:
- Increase `MIN_DURATION_SEC`
- Add to `NEGATIVE_TITLE_HARD`
- Adjust scoring thresholds

---

## Next Steps

1. **Add more artists** to `artists.csv`
2. **Tune filters** in `config.py`
3. **Set up automation** with cron
4. **Monitor quota usage** regularly
5. **Review rejected videos** in `failed.json`
6. **Manually curate** `review.json` videos

---

## Getting Help

- Check logs with `--log-level DEBUG`
- Review `out/artists/{artist}/failed.json` for rejection reasons
- Check `cache/` for state issues
- Verify credentials are correct
- Test with single artist first

---

## Security Checklist

- [ ] API keys stored in environment variables (not committed)
- [ ] `auth/` directory is gitignored
- [ ] OAuth token file has restricted permissions (600)
- [ ] API keys restricted to YouTube Data API v3
- [ ] OAuth scope limited to YouTube management
- [ ] Test with private playlist first
- [ ] Regular key rotation schedule

---

**You're all set!** Run discovery and enjoy your automatically curated music video playlist.