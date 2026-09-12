#!/bin/sh
set -eu
if [ "${1:-}" = python ] && [ "${2:-}" = manage.py ] && [ "${3:-}" = runserver ]; then
    python manage.py migrate --noinput
    python manage.py bootstrap_catalog
fi
exec "$@"
