from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase

from .models import Category, CustomerProfile, Product, ProductVariant


class CartPersistenceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.password = 'Cedar!Meadow8742'
        self.user = get_user_model().objects.create_user(
            username='cart@example.com', email='cart@example.com', password=self.password,
        )
        self.other = get_user_model().objects.create_user(username='other@example.com')
        category = Category.objects.create(name='Malas', slug='malas')
        self.product = Product.objects.create(name='Mala', slug='mala', category=category, price=100)
        self.key = str(self.product.pk)

    def login(self, client):
        response = client.post('/account/login/', {'username': self.user.email, 'password': self.password})
        self.assertEqual(response.status_code, 302)

    def add(self, client, data=None):
        return client.post(f'/cart/add/{self.product.pk}/', data or {})

    def test_logout_login_restores_cart_and_does_not_expose_it_to_others(self):
        self.login(self.client)
        self.add(self.client)
        self.client.post('/account/logout/')
        self.assertEqual(self.client.get('/cart/').context['items'], [])
        self.client.force_login(self.other)
        self.assertEqual(self.client.get('/cart/').context['items'], [])
        self.client.post('/account/logout/')
        self.login(self.client)
        self.assertEqual(self.client.get('/cart/').context['items'][0]['qty'], 1)

    def test_guest_cart_merges_once_and_survives_new_browser(self):
        self.login(self.client)
        self.add(self.client)
        browser = Client()
        self.add(browser)
        self.login(browser)
        self.assertEqual(browser.get('/cart/').context['items'][0]['qty'], 2)
        browser.post('/account/logout/')
        self.login(browser)
        self.assertEqual(browser.get('/cart/').context['items'][0]['qty'], 2)

    def test_stale_browser_logout_does_not_restore_removed_items(self):
        self.login(self.client)
        self.add(self.client)
        browser = Client()
        self.login(browser)
        browser.post(f'/cart/remove/{self.key}/')
        self.client.post('/account/logout/')
        self.login(self.client)
        self.assertEqual(self.client.get('/cart/').context['items'], [])
        self.assertEqual(CustomerProfile.objects.get(user=self.user).cart, {})

    def test_variant_and_stock_adjustment_persist(self):
        variant = ProductVariant.objects.create(product=self.product, name='Large', price=150, stock_quantity=5)
        self.login(self.client)
        self.add(self.client, {'variant': variant.pk})
        self.add(self.client, {'variant': variant.pk})
        variant.stock_quantity = 1
        variant.save()
        self.client.post('/account/logout/')
        self.login(self.client)
        item = self.client.get('/cart/').context['items'][0]
        self.assertEqual((item['variant'].pk, item['qty']), (variant.pk, 1))
        self.assertEqual(CustomerProfile.objects.get(user=self.user).cart, {f'{self.key}:{variant.pk}': 1})

    def test_guest_signup_saves_cart(self):
        self.add(self.client)
        self.client.post('/account/register/', {
            'first_name': 'Asha', 'email': 'asha@example.com',
            'password1': self.password, 'password2': self.password,
        })
        self.assertEqual(CustomerProfile.objects.get(user__username='asha@example.com').cart, {self.key: 1})

    def test_legacy_session_cart_survives_logout(self):
        self.login(self.client)
        session = self.client.session
        session.pop('cart_owner', None)
        session['cart'] = {self.key: 1}
        session.save()
        self.client.post('/account/logout/')
        self.login(self.client)
        self.assertEqual(self.client.get('/cart/').context['items'][0]['qty'], 1)

    def test_two_browsers_add_to_latest_saved_cart(self):
        self.login(self.client)
        browser = Client()
        self.login(browser)
        self.add(self.client)
        self.add(browser)
        self.assertEqual(self.client.get('/cart/').context['items'][0]['qty'], 2)
        self.assertEqual(browser.get('/account/').context['cart_count'], 2)

    def test_unavailable_items_are_removed_from_saved_cart(self):
        self.login(self.client)
        self.add(self.client)
        self.product.available = False
        self.product.save()
        self.assertEqual(self.client.get('/cart/').context['items'], [])
        self.assertEqual(CustomerProfile.objects.get(user=self.user).cart, {})
