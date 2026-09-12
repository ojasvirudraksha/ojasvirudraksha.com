from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Category, CustomerProfile, InformationPage, Product, WishlistItem


class BrandingTests(TestCase):
    def test_brand_migration_preserves_customer_product_links_and_merchant_copy(self):
        category = Category.objects.create(name='Rudraksha', slug='rudraksha')
        product = Product.objects.create(
            category=category, name='Astrol 7 Mukhi Rudraksha',
            slug='astrol-7-mukhi-rudraksha', price=700,
            description='ASTROL selection. Merchant care notes about astrology.',
        )
        user = get_user_model().objects.create_user(username='existing-customer')
        CustomerProfile.objects.create(user=user, cart={str(product.pk): 2})
        WishlistItem.objects.create(user=user, product=product)
        page = InformationPage.objects.create(
            slug='brand-test', title='Contact ASTROL', intro='Your Astrol guide', body='Merchant notes.',
        )
        migration = import_module('store.migrations.0010_ojasvirudraksha_brand')
        schema_editor = SimpleNamespace(connection=SimpleNamespace(alias='default'))
        migration.update_brand(apps, schema_editor)
        migration.update_brand(apps, schema_editor)
        product.refresh_from_db()
        page.refresh_from_db()
        self.assertEqual(product.slug, 'ojasvirudraksha-7-mukhi-rudraksha')
        self.assertEqual(product.description, 'OJASVIRUDRAKSHA selection. Merchant care notes about astrology.')
        self.assertEqual(page.title, 'Contact OJASVIRUDRAKSHA')
        self.assertEqual(page.body, 'Merchant notes.')
        self.assertEqual(CustomerProfile.objects.get(user=user).cart, {str(product.pk): 2})
        self.assertEqual(WishlistItem.objects.get(user=user).product_id, product.pk)
        self.assertRedirects(
            self.client.get('/product/astrol-7-mukhi-rudraksha/'),
            product.get_absolute_url(), status_code=301,
        )

    def test_storefront_uses_new_wordmark_and_brand(self):
        for url in ('/', '/account/login/', '/contact/'):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, 'images/ojasvirudraksha-logo.svg')
                self.assertNotContains(response, 'images/exact/logo.png')
                self.assertNotContains(response, 'ASTROL')
