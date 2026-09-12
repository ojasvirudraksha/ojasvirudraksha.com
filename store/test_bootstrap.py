from io import StringIO
from unittest.mock import patch
from django.test import TestCase
from django.core.management import call_command
from store.models import Category, Product

class BootstrapTests(TestCase):
    def test_existing_catalog_is_not_reseeded(self):
        category = Category.objects.create(name='Custom', slug='custom')
        product = Product.objects.create(name='Owner edit', slug='owner-edit', category=category, price=99)
        with patch('store.management.commands.bootstrap_catalog.call_command') as seed:
            call_command('bootstrap_catalog', stdout=StringIO())
            seed.assert_not_called()
        product.refresh_from_db()
        self.assertEqual(product.price, 99)

    def test_empty_catalog_seeds_both_sources(self):
        with patch('store.management.commands.bootstrap_catalog.call_command') as seed:
            call_command('bootstrap_catalog', stdout=StringIO())
            self.assertEqual([c.args[0] for c in seed.call_args_list], ['seed_astrol', 'import_reference_catalog'])
