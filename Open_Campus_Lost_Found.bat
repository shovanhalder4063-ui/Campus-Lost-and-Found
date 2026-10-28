@echo off
setlocal
title Campus Lost and Found Portal

REM Always run from the folder containing this BAT file.
cd /d "%~dp0"

echo ==========================================
echo   Campus Lost and Found Portal
echo ==========================================
echo.

REM Check that the Flask application is in this folder.
if not exist "app.py" (
    echo ERROR: app.py was not found.
    echo Move this BAT file into the same folder as app.py.
    echo.
    pause
    exit /b 1
)

REM Create a virtual environment on the first run.
if not exist "venv\Scripts\python.exe" (
    echo First-time setup: creating a Python virtual environment...
    py -m venv venv
    if errorlevel 1 (
        echo Could not create the virtual environment.
        echo Make sure Python is installed and available from the command line.
        pause
        exit /b 1
    )
)

REM Install dependencies on first run, after requirements change, or if Flask-Migrate is missing.
set "INSTALL_DEPS="
if not exist "venv\.dependencies_installed" set "INSTALL_DEPS=1"
"venv\Scripts\python.exe" -c "import flask_migrate" >nul 2>&1
if errorlevel 1 set "INSTALL_DEPS=1"
if defined INSTALL_DEPS (
    echo Installing required libraries. This may take a few minutes...
    "venv\Scripts\python.exe" -m pip install --upgrade pip
    "venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo Dependency installation failed. Check your internet connection
        echo and make sure requirements.txt is present.
        pause
        exit /b 1
    )
    echo installed>"venv\.dependencies_installed"
)

echo Applying database migrations...
"venv\Scripts\python.exe" -m flask --app app db upgrade
if errorlevel 1 (
    echo.
    echo Database migration failed.
    echo If this is an existing database, back it up and follow the migration
    echo instructions in README.md before running the launcher again.
    pause
    exit /b 1
)

echo.
echo Starting the website...
echo Your browser will open at http://127.0.0.1:5000
echo Keep this black window open while using the website.
echo To stop the website, close this window or press Ctrl+C.
echo.

REM Open the browser a few seconds after the server starts.
start "" cmd /c "timeout /t 3 /nobreak >nul & start "" http://127.0.0.1:5000"

REM Run Flask in this window.
"venv\Scripts\python.exe" app.py

echo.
echo The website server has stopped.
pause
