@echo off
title SocailManager - Automated Unit Tests
echo =======================================================
echo          Running SocailManager Test Suite...
echo =======================================================
echo.
cd /d "%~dp0"
if exist ".venv\Scripts\pytest.exe" (
    ".venv\Scripts\pytest.exe" -v
) else (
    echo [ERROR] pytest not found in .venv.
)
echo.
echo =======================================================
echo Tests completed. Press any key to close this window.
echo =======================================================
pause
