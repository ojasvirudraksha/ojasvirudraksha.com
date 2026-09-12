#!/bin/bash
set -e
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py seed_astrol
python manage.py import_reference_catalog
echo ""
echo "ASTROL setup complete."
echo "Run: source .venv/bin/activate && python manage.py runserver"
echo "Then open http://127.0.0.1:8000/"
