#!/usr/bin/env bash

# =============================
# CONFIG
# =============================
PYTHON="python3"
ARTISTS_CSV="muchloud_artists.csv"
PLAYLIST_ID="PLa73YkAc2TvLqEb9gqMHnmjoN30qpnPe3"

# =============================
# ENVIRONMENT CHECK
# =============================
echo "Checking environment setup..."

# Check if virtual environment should be activated
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if .env file exists
if [ -f ".env" ]; then
    echo "Found .env file - loading environment variables..."
    # Load .env file (dotenv will be loaded by Python scripts automatically)
    export $(grep -v '^#' .env | xargs)
fi

# Verify API keys are set
if ! $PYTHON -c "import os; keys = os.environ.get('YOUTUBE_API_KEYS', ''); exit(0 if keys else 1)" 2>/dev/null; then
    echo "[ERROR] YOUTUBE_API_KEYS not set!"
    echo ""
    echo "Please set environment variables:"
    echo "  Option 1: Create .env file with YOUTUBE_API_KEYS=key1,key2,key3"
    echo "  Option 2: Run: export YOUTUBE_API_KEYS=key1,key2,key3"
    echo "  Option 3: Add to ~/.bashrc or ~/.zshrc"
    echo ""
    exit 1
fi

echo "Environment OK - API keys found"
echo ""

# ============================================================
# 1. DISCOVERY
# ============================================================

echo "============================================"
echo "Running discovery for $ARTISTS_CSV"
echo "============================================"
echo ""

$PYTHON discover_music_videos.py "$ARTISTS_CSV" "$@"
DISCOVERY_EXIT=$?

if [ $DISCOVERY_EXIT -eq 2 ]; then
    echo "[INFO] Discovery stopped due to quota exhaustion - this is normal"
elif [ $DISCOVERY_EXIT -ne 0 ]; then
    echo "[WARN] Discovery exited with code $DISCOVERY_EXIT - continuing"
fi

# ============================================================
# 2. PLAYLIST INVALIDATION (PLAN)
# ============================================================

echo ""
echo "============================================"
echo "Planning playlist invalidation"
echo "============================================"
echo ""

$PYTHON playlist_invalidate.py "$ARTISTS_CSV" "$PLAYLIST_ID"
INVALIDATE_PLAN_EXIT=$?

if [ $INVALIDATE_PLAN_EXIT -ne 0 ]; then
    echo "[WARN] Invalidation planning exited with code $INVALIDATE_PLAN_EXIT"
    echo "This step is optional - continuing"
fi

# ============================================================
# 3. PLAYLIST INVALIDATION (APPLY)
# ============================================================

echo ""
echo "============================================"
echo "Applying playlist invalidation"
echo "============================================"
echo ""

$PYTHON playlist_apply_invalidation.py "$PLAYLIST_ID"
INVALIDATE_APPLY_EXIT=$?

if [ $INVALIDATE_APPLY_EXIT -ne 0 ]; then
    echo "[WARN] Invalidation apply exited with code $INVALIDATE_APPLY_EXIT"
    echo "This step is optional - continuing"
fi

# ============================================================
# 4. PLAYLIST SYNC
# ============================================================

echo ""
echo "============================================"
echo "Syncing playlist $PLAYLIST_ID"
echo "============================================"
echo ""

$PYTHON youtube_playlist_sync.py "$ARTISTS_CSV" "$PLAYLIST_ID" "$@"
PLAYLIST_EXIT=$?

if [ $PLAYLIST_EXIT -eq 1 ]; then
    echo "[WARN] Playlist sync had errors - check logs above"
elif [ $PLAYLIST_EXIT -eq 2 ]; then
    echo "[INFO] Playlist sync stopped due to quota - safe to rerun later"
elif [ $PLAYLIST_EXIT -ne 0 ]; then
    echo "[WARN] Playlist sync exited with code $PLAYLIST_EXIT"
fi

# ============================================================
# SUMMARY
# ============================================================

echo ""
echo "============================================"
echo "Pipeline finished"
echo "============================================"
echo "Discovery exit code:         $DISCOVERY_EXIT"
echo "Invalidate plan exit code:   $INVALIDATE_PLAN_EXIT"
echo "Invalidate apply exit code:  $INVALIDATE_APPLY_EXIT"
echo "Playlist sync exit code:     $PLAYLIST_EXIT"
echo "============================================"
echo ""

# Interpret results
if [ $DISCOVERY_EXIT -eq 0 ] && [ $PLAYLIST_EXIT -eq 0 ]; then
    echo "[SUCCESS] All steps completed successfully!"
else
    echo "[INFO] Some steps had issues - check codes above"
    echo "Exit code 2 usually means quota exhausted - rerun tomorrow"
fi

echo ""