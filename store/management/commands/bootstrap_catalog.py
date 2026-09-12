from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from store.models import Product


class Command(BaseCommand):
    help = 'Populate an empty development catalog; never overwrite an existing catalog.'

    @transaction.atomic
    def handle(self, **options):
        if Product.objects.exists():
            self.stdout.write('Existing catalog preserved.')
            return
        call_command('seed_astrol', stdout=self.stdout)
        call_command('import_reference_catalog', stdout=self.stdout)
