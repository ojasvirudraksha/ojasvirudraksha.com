import json
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from store.models import Product


class Command(BaseCommand):
    help = 'Apply the original OJASVIRUDRAKSHA description catalog, preserving other product fields.'

    def add_arguments(self, parser):
        parser.add_argument('--catalog', type=Path, default=settings.BASE_DIR / 'store/data/product_descriptions.json')
        parser.add_argument('--overwrite', action='store_true', help='Replace existing descriptions; a backup is written first.')
        parser.add_argument('--dry-run', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            rows = json.loads(options['catalog'].read_text())['products']
            updates = []
            for row in rows:
                if not row['description'].strip() or not 0 < len(row['short_description']) <= 240:
                    raise ValueError('Descriptions must be nonempty and summaries at most 240 characters.')
                lookup = {'source_id': row['source_id']} if row.get('source_id') else {'slug': row['slug']}
                product = Product.objects.filter(**lookup).first()
                if product is None:
                    continue
                old = {'short_description': product.short_description, 'description': product.description}
                new = {key: row[key] for key in old}
                if old == new:
                    continue
                placeholder = not product.description.strip() or any(marker in product.description for marker in (
                    'Prototype product listing for the local Ojasvirudraksha storefront.',
                    'Choose an available option above to see its price.',
                    'This sample shows how the OJASVIRUDRAKSHA collection will look.',
                ))
                if options['overwrite'] or placeholder:
                    updates.append((product, old, new))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise CommandError(f'Invalid description catalog: {exc}') from exc
        if options['dry_run']:
            self.stdout.write(f'{len(updates)} descriptions would change.')
            return
        if updates:
            directory = settings.BASE_DIR / '.local/description-backups'
            directory.mkdir(parents=True, exist_ok=True)
            filename = directory / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
            filename.write_text(json.dumps([
                {'id': p.id, 'slug': p.slug, 'source_id': p.source_id, **old}
                for p, old, new in updates
            ], ensure_ascii=False, indent=2))
            for product, old, new in updates:
                Product.objects.filter(pk=product.pk).update(**new)
            self.stdout.write(f'Previous descriptions saved to {filename}')
        self.stdout.write(self.style.SUCCESS(f'Updated {len(updates)} product descriptions.'))
