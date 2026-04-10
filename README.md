# FitLife Studio – Digital Time Tracking (Stempeluhr)

A Django-based punch clock / time tracking application for a fitness studio, featuring employee clock-in/out with breaks, HR dashboard with monthly reporting, and CSV export.

## Tech Stack

- **Backend:** Python 3, Django 5.x, SQLite
- **Frontend:** Vanilla HTML/JS, Bootstrap 5 (CDN), strict dark mode
- **i18n:** Custom JS-based EN/DE toggle (no Django i18n framework)

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Seed demo data
python manage.py seed

# Start the development server
python manage.py runserver
```

## Demo Credentials

| Role     | Username | Password |
|----------|----------|----------|
| Employee | lisa     | 1234     |
| Employee | tom      | 2345     |
| Employee | klara    | 3456     |
| Employee | max      | 4567     |
| Employee | anna     | 5678     |
| HR Admin | hr       | hr1234   |

## Features

- **PIN Login:** Visual numeric keypad for quick employee login
- **Punch Clock:** AJAX-based clock-in/out and break tracking with real-time state machine UI
- **Weekly Overview:** Employees see their last 7 days with correction submission for missing clock-outs
- **HR Dashboard:** Monthly overview with target vs actual hours, expandable day-by-day detail rows
- **Conditional Styling:** Deficit (>5h) highlighted red, overtime (>5h) highlighted yellow
- **HR Actions:** Send reminder emails (mock) and acknowledge reviews via AJAX
- **CSV Export:** Download monthly time reports as CSV
- **Dark Mode:** Full Bootstrap 5 dark theme
- **Bilingual:** EN/DE toggle via JavaScript with `data-en` / `data-de` attributes
