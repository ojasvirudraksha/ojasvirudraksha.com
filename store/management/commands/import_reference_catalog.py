import json
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import transaction
from django.utils.text import slugify
from store.models import Category, Product, ProductVariant

CATEGORIES = {
    'rudraksha': ('Rudraksha', 'Sacred beads, selected by origin and Mukhi.'),
    'malas': ('Malas', 'Rudraksha, wood, stone and crystal malas for your daily practice.'),
    'bracelets': ('Bracelets', 'Rudraksha, crystal and wood bracelets.'),
    'gemstones': ('Gemstones', 'Explore gemstone styles. Sample listings shown for now.'),
    'rings': ('Rings', 'Explore ring styles. Sample listings shown for now.'),
    'pearls': ('Pearls', 'Pearl and Rudraksha pearl malas.'),
    'shankh': ('Shankh', 'Traditional conch shells. Sample listings shown for now.'),
    'tulsi-mala': ('Tulsi Mala', 'Tulsi bead malas for japa and devotion.'),
    'dhan-yog': ('Dhan Yog', 'Pyrite bracelets and traditional prosperity-themed combinations.'),
    'shaligram': ('Shaligram', 'Individual Shaligram stones for traditional puja.'),
    'kavach': ('Kavach', 'Traditional Rudraksha combinations and kavach.'),
    'yantras': ('Yantras', 'Sphatik yantras and Shivling selections.'),
}
SAMPLES = [
    ('Ruby Gemstone', 'gemstones', 'gem-5.png', '4500'),
    ('Emerald Gemstone', 'gemstones', 'gem-4.png', '5500'),
    ('Yellow Sapphire Gemstone', 'gemstones', 'gem-2.png', '6500'),
    ('Blue Sapphire Gemstone', 'gemstones', 'gem-3.png', '7500'),
    ('Amethyst Gemstone', 'gemstones', 'gem-1.png', '1500'),
    ('Gemstone Ring', 'rings', 'ring.png', '3500'),
    ('Puja Shankh', 'shankh', 'shankh.png', '1800'),
]


class Command(BaseCommand):
    help = 'Import the saved reference catalog and local sample listings without changing existing products.'

    def add_arguments(self, parser):
        parser.add_argument('--catalog', type=Path, default=settings.BASE_DIR / 'store/data/rudradhyay_catalog.json')

    @transaction.atomic
    def handle(self, *args, **options):
        data = json.loads(options['catalog'].read_text())
        rows = data['products']
        for row in rows:
            if not (settings.BASE_DIR / 'static' / row['image']).is_file():
                raise CommandError(f"Missing local image: {row['image']}")
        categories = {slug: Category.objects.get_or_create(slug=slug, defaults={'name': name, 'description': description})[0]
                      for slug, (name, description) in CATEGORIES.items()}
        created = 0
        for row in rows:
            candidates = [v for v in row['variants'] if v['available'] and Decimal(v['price']) > 0]
            default = min(candidates or row['variants'], key=lambda v: Decimal(v['price']))
            description = f"{row['name']}. Explore the available options for this {categories[row['category']].name.lower()} selection."
            # Source IDs make repeat imports safe and preserve later merchant edits.
            product, new = Product.objects.get_or_create(source_id=row['source_id'], defaults={
                'slug': f"{slugify(row['name'])[:150]}-{row['source_id']}",
                'name': row['name'], 'category': categories[row['category']],
                'origin': row['origin'], 'price': default['price'],
                'compare_at_price': default['compare_at_price'], 'image': row['image'],
                'short_description': description[:240],
                'description': (f"{row['name']}\n\n" + (f"Origin listed: {row['origin']}.\n\n" if row['origin'] else '')
                                + 'Choose an available option above to see its price. Natural materials can vary in colour, texture and shape.'),
                'available': bool(candidates), 'source_url': row['source_url'],
            })
            if not new:
                continue
            created += 1
            ProductVariant.objects.bulk_create([
                ProductVariant(product=product, source_id=v['source_id'], name=v['name'], sku=v['sku'] or '',
                               price=v['price'], compare_at_price=v['compare_at_price'],
                               available=v['available'] and Decimal(v['price']) > 0, position=i)
                for i, v in enumerate(row['variants'])
            ])
            if row['dhan_yog']:
                product.collections.add(categories['dhan-yog'])
        samples = 0
        for name, category, image, price in SAMPLES:
            _, new = Product.objects.get_or_create(slug='sample-'+slugify(name), defaults={
                'name': name, 'category': categories[category], 'image': 'images/products/'+image,
                'price': price, 'is_sample': True, 'available': False,
                'short_description': 'Sample product — illustrative image and price. Not available to purchase.',
                'description': 'This sample shows how the OJASVIRUDRAKSHA collection will look. The image and price are illustrative; product specifications, availability and final pricing have not been supplied.',
            })
            samples += int(new)
        self.stdout.write(self.style.SUCCESS(f'Added {created} reference products and {samples} samples. Existing products preserved.'))
        call_command('update_product_descriptions', stdout=self.stdout)
