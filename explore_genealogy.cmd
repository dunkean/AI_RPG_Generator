@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Missing .venv. Run: python -m venv .venv
    echo Then run: .venv\Scripts\python.exe -m pip install -e ".[dev]"
    pause
    exit /b 1
)
set "GENEALOGY_ARCHIVE=output\genealogy\demo_world.sqlite"
if not "%~1"=="" set "GENEALOGY_ARCHIVE=%~1"
if not exist "%GENEALOGY_ARCHIVE%" (
    if not "%~1"=="" (
        echo Archive not found: "%GENEALOGY_ARCHIVE%"
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -m src.genealogy.cli generate config/genealogy/fantasy.yaml --output "%GENEALOGY_ARCHIVE%"
    if errorlevel 1 (
        pause
        exit /b 1
    )
)
echo Open http://127.0.0.1:8765 in your browser. Keep this window open.
echo Using saved archive: "%GENEALOGY_ARCHIVE%". YAML edits do not regenerate it.
".venv\Scripts\python.exe" -m src.genealogy.cli explore "%GENEALOGY_ARCHIVE%"
if errorlevel 1 pause
