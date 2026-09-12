import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.template import Context, Template
from django.test import TestCase

from store.models import Category, Product


class ProductDescriptionTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Rudraksha', slug='rudraksha')
        self.product = Product.objects.create(
            category=self.category, name='Test bead', slug='test-bead', price='1200',
            source_id='123', stock_quantity=8, description='Prototype product listing for the local Ojasvirudraksha storefront.',
        )

    def catalog(self, root):
        path = Path(root) / 'catalog.json'
        path.write_text(json.dumps({'products': [{
            'slug': 'old-slug', 'source_id': '123',
            'short_description': 'Original summary',
            'description': 'An original introduction.\n\nCare guidance\nWipe gently.',
        }]}))
        return path

    def test_updates_only_descriptions_and_backs_up_once(self):
        with TemporaryDirectory() as root, self.settings(BASE_DIR=Path(root)):
            path = self.catalog(root)
            call_command('update_product_descriptions', catalog=path, dry_run=True, stdout=StringIO())
            self.product.refresh_from_db()
            self.assertIn('Prototype', self.product.description)
            call_command('update_product_descriptions', catalog=path, stdout=StringIO())
            self.product.refresh_from_db()
            self.assertEqual(self.product.short_description, 'Original summary')
            self.assertEqual(self.product.stock_quantity, 8)
            self.assertEqual(self.product.price, 1200)
            self.assertEqual(self.product.slug, 'test-bead')
            backups = list((Path(root) / '.local/description-backups').glob('*.json'))
            self.assertEqual(len(backups), 1)
            self.assertIn('Prototype', json.loads(backups[0].read_text())[0]['description'])
            call_command('update_product_descriptions', catalog=path, stdout=StringIO())
            self.assertEqual(len(list(backups[0].parent.glob('*.json'))), 1)

    def test_preserves_merchant_edit_unless_overwrite_requested(self):
        self.product.description = 'The owner has edited this description.'
        self.product.save()
        with TemporaryDirectory() as root, self.settings(BASE_DIR=Path(root)):
            path = self.catalog(root)
            call_command('update_product_descriptions', catalog=path, stdout=StringIO())
            self.product.refresh_from_db()
            self.assertEqual(self.product.description, 'The owner has edited this description.')
            call_command('update_product_descriptions', catalog=path, overwrite=True, stdout=StringIO())
            self.product.refresh_from_db()
            self.assertIn('An original introduction.', self.product.description)

    def test_sections_escape_html_and_preserve_plain_descriptions(self):
        template = Template('{% load product_content %}{% for s in value|description_sections %}<h3>{{ s.heading }}</h3>{{ s.body|linebreaks }}{% endfor %}')
        result = template.render(Context({'value': 'Plain introduction.\n\nCare guidance\n<script>alert(1)</script>'}))
        self.assertIn('Plain introduction.', result)
        self.assertIn('<h3>Care guidance</h3>', result)
        self.assertNotIn('<script>', result)
        self.assertIn('&lt;script&gt;', result)
