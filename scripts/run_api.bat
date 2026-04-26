@echo off
REM SmartStock API Server - Windows launch script
REM Run from project root.
cd /d "%~dp0\.."
set "PY=.venv\Scripts\python.exe"

if not exist "%PY%" (
    echo [ERROR] Virtual environment not found at %PY%
    echo Create it first, then install dependencies:
    echo   py -m venv .venv
    echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
    exit /b 1
)

echo.
echo  SmartStock FastAPI Server
echo  ============================================================
echo  API docs   : http://localhost:8000/docs
echo  Health     : http://localhost:8000/health
echo  ============================================================
echo.
"%PY%" -m uvicorn smartstock.api.main:app --reload --host 0.0.0.0 --port 8000
