from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase, Client, RequestFactory
from store.currency import market, convert, format_money, validate_rates
from store.models import Product, Category, ProductVariant

RATES = {'rates': {'INR': 1, 'USD': 0.012, 'JPY': 1.8, 'KWD': 0.0037}, 'time_last_update_unix': 1789084800}

@patch('store.currency.rates', return_value=RATES)
class CurrencyTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Rudraksha', slug='rudraksha')
        self.product = Product.objects.create(name='Bead', slug='bead', category=self.category, price='1000.55')

    def test_country_post_persists_and_rejects_invalid_redirect(self, rates):
        response = self.client.post('/country/', {'country': 'US', 'next': '/shop/?category=rudraksha&sort=price-asc'})
        self.assertEqual(response.url, '/shop/?category=rudraksha&sort=price-asc')
        self.assertEqual(response.cookies['ojasvirudraksha_country'].value, 'US')
        self.assertContains(self.client.get('/product/bead/'), 'USD 12.01')
        self.assertEqual(self.client.post('/country/', {'country': 'US', 'next': 'https://evil.example/'}).url, '/')
        self.assertEqual(self.client.post('/country/', {'country': 'invalid'}).status_code, 400)
        self.assertEqual(self.client.get('/country/').status_code, 405)
        self.assertEqual(Client(enforce_csrf_checks=True).post('/country/', {'country': 'US'}).status_code, 403)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal('1000.55'))

    def test_cart_rounds_units_and_total_consistently(self, rates):
        self.client.cookies['ojasvirudraksha_country'] = 'US'
        session=self.client.session
        session['cart']={str(self.product.pk): 3}
        session.save()
        response=self.client.get('/cart/')
        self.assertEqual(response.context['display_total'], Decimal('36.03'))
        self.assertEqual(response.context['total'], Decimal('3001.65'))
        self.assertContains(response, 'USD 36.03')

    def test_variant_and_filter_labels_use_currency(self, rates):
        ProductVariant.objects.create(product=self.product, name='Large', price='2000', available=True)
        self.client.cookies['ojasvirudraksha_country']='US'
        self.assertContains(self.client.get('/product/bead/'), 'data-price="USD 24.00"')
        response=self.client.get('/shop/?price=under-3000')
        self.assertContains(response, 'Under USD 36.00')
        self.assertNotContains(response, 'Under ₹')

    def test_currency_precision_and_missing_rate_fallback(self, rates):
        request=RequestFactory().get('/', HTTP_COOKIE='ojasvirudraksha_country=JP')
        self.assertEqual(format_money(100, market(request)), 'JPY 180')
        request=RequestFactory().get('/', HTTP_COOKIE='ojasvirudraksha_country=KW')
        self.assertEqual(format_money(100, market(request)), 'KWD 0.370')
        request=RequestFactory().get('/', HTTP_COOKIE='ojasvirudraksha_country=GB')
        self.assertEqual(market(request)['currency'], 'USD')
        self.assertTrue(market(request)['fallback'])
        request=RequestFactory().get('/', HTTP_COOKIE='ojasvirudraksha_country=invalid')
        self.assertEqual(market(request)['currency'], 'INR')

    def test_default_prices_retain_paise(self, rates):
        self.assertContains(self.client.get('/product/bead/'), '₹ 1,000.55')

class RateValidationTests(TestCase):
    def test_invalid_download_rejected(self):
        for value in ('NaN', '-1', '0', 'Infinity'):
            with self.assertRaises(ValueError):
                validate_rates({'result':'success','base_code':'INR','rates':{'INR':1,'USD':value},'time_last_update_unix':1789084800})
