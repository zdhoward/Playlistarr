@echo off
setlocal

REM Resolve project root (directory of this script)
set ROOT=%~dp0

REM Prefer python from PATH / active venv
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: python not found in PATH
    exit /b 1
)

REM Run Playlistarr as a module (REQUIRED for package imports)
python -m playlistarr %*

endlocal
