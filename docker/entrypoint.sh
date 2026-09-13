#!/bin/sh
set -eu
if [ "${1:-}" = python ] && [ "${2:-}" = manage.py ] && [ "${3:-}" = runserver ]; then
    python manage.py migrate --noinput
    python manage.py bootstrap_catalog
    # The persistent local_state volume starts without exchange rates.
    # Preserve storefront availability and cached rates if the provider is down.
    python manage.py refresh_exchange_rates || echo "Warning: exchange rates could not be refreshed; using cached rates if available." >&2
fi
exec "$@"
