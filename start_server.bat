@echo off
title HudhudRadar - AI Social Media Agent Server
echo =======================================================
echo           Starting HudhudRadar Server...
echo =======================================================
echo.
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    echo [OK] Virtual environment detected.
    echo [INFO] Opening server at http://localhost:8000/dashboard
    start http://localhost:8000/dashboard
    ".venv\Scripts\python.exe" src/main.py
) else (
    echo [ERROR] Virtual environment (.venv) not found.
    echo Please create it using: python -m venv .venv
    pause
)
