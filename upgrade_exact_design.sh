#!/bin/bash
set -e
source .venv/bin/activate
python manage.py makemigrations
python manage.py migrate
python manage.py seed_astrol
echo ""
echo "ASTROL exact-design update applied."
echo "Start with: python manage.py runserver"
echo "Open: http://127.0.0.1:8000/"
