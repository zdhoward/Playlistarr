@echo off
setlocal

set ROOT=%~dp0
set BIN=%USERPROFILE%\bin

echo Installing Playlistarr...

if not exist "%BIN%" (
    mkdir "%BIN%"
)

REM Create launcher
set TARGET=%BIN%\playlistarr.cmd

echo @echo off > "%TARGET%"
echo "%ROOT%\playlistarr.cmd" %%* >> "%TARGET%"

REM Add to PATH if not present
echo %PATH% | find "%BIN%" >nul
if errorlevel 1 (
    setx PATH "%PATH%;%BIN%"
    echo Added %BIN% to PATH (restart terminal to take effect)
)

echo.
echo Playlistarr installed!
echo You can now run: playlistarr sync muchloud
