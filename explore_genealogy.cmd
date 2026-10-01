@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Missing .venv. Run: python -m venv .venv
    echo Then run: .venv\Scripts\python.exe -m pip install -e ".[dev]"
    pause
    exit /b 1
)
echo Open http://127.0.0.1:8768 in your browser. Keep this window open.
echo Binary worlds stay in memory. No automatic files or SQLite writes.
if not "%~1"=="" (
    ".venv\Scripts\python.exe" -m src.genealogy.cli explore "%~1" --port 8768
) else (
    ".venv\Scripts\python.exe" -m src.genealogy.cli studio --port 8768
)
if errorlevel 1 pause
