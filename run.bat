@echo off
echo ============================================
echo   FitLife Studio - Time Tracker Setup
echo ============================================
echo.

REM Detect Python command
where python >nul 2>nul
if %errorlevel%==0 (
    set PY=python
) else (
    where python3 >nul 2>nul
    if %errorlevel%==0 (
        set PY=python3
    ) else (
        echo Error: Python is not installed. Please install Python 3.8+ and try again.
        pause
        exit /b 1
    )
)

echo Using Python:
%PY% --version

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    %PY% -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Run migrations
echo Running database migrations...
python manage.py makemigrations tracker --no-input
python manage.py migrate --no-input

REM Seed demo data (ignore errors if already seeded)
echo Seeding demo data...
python manage.py seed 2>nul

echo.
echo ============================================
echo   Setup complete!
echo ============================================
echo.
echo Login credentials:
echo   Employees: lisa/1234, tom/2345, klara/3456, max/4567, anna/5678
echo   HR Admin:  hr/hr1234
echo.
echo Starting server at http://127.0.0.1:8000
echo Press Ctrl+C to stop.
echo.

python manage.py runserver
