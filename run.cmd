@echo off
setlocal

REM =============================
REM CONFIG
REM =============================
set "PYTHON=python"
set "ARTISTS_CSV=muchloud_artists.csv"
set "PLAYLIST_ID=PLa73YkAc2TvLqEb9gqMHnmjoN30qpnPe3"

REM =============================
REM ENVIRONMENT CHECK
REM =============================
echo Checking environment setup...

REM Check if virtual environment should be activated
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Check if .env file exists and load it
if exist ".env" (
    echo Found .env file - loading environment variables...
    REM Note: dotenv will be loaded by Python scripts automatically
)

REM Verify API keys are set
%PYTHON% -c "import os; keys = os.environ.get('YOUTUBE_API_KEYS', ''); exit(0 if keys else 1)" 2>nul
if errorlevel 1 (
    echo [ERROR] YOUTUBE_API_KEYS not set!
    echo.
    echo Please set environment variables:
    echo   Option 1: Create .env file with YOUTUBE_API_KEYS=key1,key2,key3
    echo   Option 2: Run: set YOUTUBE_API_KEYS=key1,key2,key3
    echo   Option 3: Set system environment variables
    echo.
    pause
    exit /b 1
)

echo Environment OK - API keys found
echo.

REM ============================================================
REM 1. DISCOVERY
REM ============================================================

echo ============================================
echo Running discovery for %ARTISTS_CSV%
echo ============================================
echo.

%PYTHON% discover_music_videos.py "%ARTISTS_CSV%" %*
set "DISCOVERY_EXIT=%ERRORLEVEL%"

if "%DISCOVERY_EXIT%"=="2" (
    echo [INFO] Discovery stopped due to quota exhaustion - this is normal
) else if not "%DISCOVERY_EXIT%"=="0" (
    echo [WARN] Discovery exited with code %DISCOVERY_EXIT% - continuing
)

REM ============================================================
REM 2. PLAYLIST INVALIDATION (PLAN)
REM ============================================================

echo.
echo ============================================
echo Planning playlist invalidation
echo ============================================
echo.

%PYTHON% playlist_invalidate.py "%ARTISTS_CSV%" "%PLAYLIST_ID%"
set "INVALIDATE_PLAN_EXIT=%ERRORLEVEL%"

if not "%INVALIDATE_PLAN_EXIT%"=="0" (
    echo [WARN] Invalidation planning exited with code %INVALIDATE_PLAN_EXIT%
    echo This step is optional - continuing
)

REM ============================================================
REM 3. PLAYLIST INVALIDATION (APPLY)
REM ============================================================

echo.
echo ============================================
echo Applying playlist invalidation
echo ============================================
echo.

%PYTHON% playlist_apply_invalidation.py "%PLAYLIST_ID%"
set "INVALIDATE_APPLY_EXIT=%ERRORLEVEL%"

if not "%INVALIDATE_APPLY_EXIT%"=="0" (
    echo [WARN] Invalidation apply exited with code %INVALIDATE_APPLY_EXIT%
    echo This step is optional - continuing
)

REM ============================================================
REM 4. PLAYLIST SYNC
REM ============================================================

echo.
echo ============================================
echo Syncing playlist %PLAYLIST_ID%
echo ============================================
echo.

%PYTHON% youtube_playlist_sync.py "%ARTISTS_CSV%" "%PLAYLIST_ID%" %*
set "PLAYLIST_EXIT=%ERRORLEVEL%"

if "%PLAYLIST_EXIT%"=="1" (
    echo [WARN] Playlist sync had errors - check logs above
) else if "%PLAYLIST_EXIT%"=="2" (
    echo [INFO] Playlist sync stopped due to quota - safe to rerun later
) else if not "%PLAYLIST_EXIT%"=="0" (
    echo [WARN] Playlist sync exited with code %PLAYLIST_EXIT%
)

REM ============================================================
REM SUMMARY
REM ============================================================

echo.
echo ============================================
echo Pipeline finished
echo ============================================
echo Discovery exit code:         %DISCOVERY_EXIT%
echo Invalidate plan exit code:   %INVALIDATE_PLAN_EXIT%
echo Invalidate apply exit code:  %INVALIDATE_APPLY_EXIT%
echo Playlist sync exit code:     %PLAYLIST_EXIT%
echo ============================================
echo.

REM Interpret results
if "%DISCOVERY_EXIT%"=="0" if "%PLAYLIST_EXIT%"=="0" (
    echo [SUCCESS] All steps completed successfully!
) else (
    echo [INFO] Some steps had issues - check codes above
    echo Exit code 2 usually means quota exhausted - rerun tomorrow
)

echo.
pause

endlocal