@echo off
:: SmartStock Dashboard Launcher
:: Run from the project root: scripts\run_dashboard.bat

cd /d "%~dp0\.."
echo Starting SmartStock Dashboard...
echo Open http://localhost:8051 in your browser.
echo.
streamlit run smartstock/dashboard/app.py --server.port 8051
