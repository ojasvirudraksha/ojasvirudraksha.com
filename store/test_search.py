from unittest.mock import patch
from django.test import TestCase
from store.models import Category, Product

class ProductSuggestionTests(TestCase):
    def setUp(self):
        self.category=Category.objects.create(name='Malas',slug='suggestion-malas')
        self.product=Product.objects.create(name='Tulsi Mala',slug='suggestion-tulsi',category=self.category,price='1200',origin='India')
        Product.objects.create(name='Hidden Tulsi',slug='suggestion-hidden',category=self.category,price=100,active=False)

    def test_empty_search_and_single_character(self):
        self.assertEqual(self.client.get('/search/suggestions/?q= ').json()['results'],[])
        data=self.client.get('/search/suggestions/?q=t').json()
        self.assertEqual([p['id'] for p in data['results']],[self.product.pk])
        self.assertEqual(data['results'][0]['url'],self.product.get_absolute_url())

    def test_multiword_case_insensitive_and_no_match(self):
        self.assertEqual(self.client.get('/search/suggestions/',{'q':'INDIA tulsi'}).json()['count'],1)
        self.assertEqual(self.client.get('/search/suggestions/',{'q':'unlistedword'}).json()['results'],[])

    def test_limit_and_exact_match_ranking(self):
        Product.objects.bulk_create([Product(name=f'Tulsi Mala {i}',slug=f'suggestion-extra-{i}',category=self.category,price=50) for i in range(12)])
        data=self.client.get('/search/suggestions/',{'q':'Tulsi Mala'}).json()
        self.assertEqual(data['count'],13)
        self.assertEqual(len(data['results']),8)
        self.assertEqual(data['results'][0]['id'],self.product.pk)

    @patch('store.currency.rates', return_value={'rates':{'INR':1,'USD':0.01},'time_last_update_unix':1789084800})
    def test_currency_and_sample_status(self,rates):
        self.client.cookies['ojasvirudraksha_country']='US'
        self.product.is_sample=True;self.product.save()
        result=self.client.get('/search/suggestions/',{'q':'Tulsi'}).json()['results'][0]
        self.assertEqual(result['price'],'USD 12.00')
        self.assertEqual(result['badge'],'Sample')
        self.assertEqual(result['price_prefix'],'Sample price')

    def test_get_only(self):
        self.assertEqual(self.client.post('/search/suggestions/',{'q':'Tulsi'}).status_code,405)
