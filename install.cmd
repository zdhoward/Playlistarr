@echo off
setlocal

set BIN=%USERPROFILE%\bin

echo Installing Playlistarr...

if not exist "%BIN%" (
    mkdir "%BIN%"
)

set TARGET=%BIN%\playlistarr.cmd

echo @echo off > "%TARGET%"
echo python -m playlistarr %%* >> "%TARGET%"

REM Add BIN to PATH if needed
echo %PATH% | find "%BIN%" >nul
if errorlevel 1 (
    setx PATH "%PATH%;%BIN%"
    echo Added %BIN% to PATH (restart terminal required)
)

echo.
echo Playlistarr installed!
echo You can now run:
echo   playlistarr sync muchloud

endlocal
