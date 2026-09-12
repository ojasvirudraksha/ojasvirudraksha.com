import json
import os
import tempfile
from urllib.request import urlopen
from django.core.management.base import BaseCommand, CommandError
from store.currency import rate_path, validate_rates

class Command(BaseCommand):
    help = 'Refresh the cached INR exchange rates. Schedule once daily; failures preserve the previous rates.'

    def handle(self, **options):
        try:
            with urlopen('https://open.er-api.com/v6/latest/INR', timeout=15) as response:
                data = json.load(response)
            validate_rates(data)
            path = rate_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as file:
                json.dump(data, file)
                temporary = file.name
            os.replace(temporary, path)
        except Exception as exc:
            raise CommandError(f'Rates could not be refreshed; existing rates retained: {exc}') from exc
        self.stdout.write(self.style.SUCCESS(f"Cached {len(data['rates'])} exchange rates."))
