#!/bin/bash
set -e

echo "============================================"
echo "  FitLife Studio - Time Tracker Setup"
echo "============================================"
echo ""

# Detect Python command
if command -v python3 &> /dev/null; then
    PY=python3
elif command -v python &> /dev/null; then
    PY=python
else
    echo "Error: Python is not installed. Please install Python 3.8+ and try again."
    exit 1
fi

echo "Using Python: $($PY --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    $PY -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run migrations
echo "Running database migrations..."
python manage.py makemigrations tracker --no-input
python manage.py migrate --no-input

# Seed demo data (ignore errors if already seeded)
echo "Seeding demo data..."
python manage.py seed || true

echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""
echo "Login credentials:"
echo "  Employees: lisa/1234, tom/2345, klara/3456, max/4567, anna/5678"
echo "  HR Admin:  hr/hr1234"
echo ""
echo "Starting server at http://127.0.0.1:8000"
echo "Press Ctrl+C to stop."
echo ""

python manage.py runserver
