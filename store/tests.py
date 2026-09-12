from django.test import TestCase
from .models import Category, Product


class CollectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        rudraksha = Category.objects.create(name="Rudraksha", slug="rudraksha")
        Category.objects.create(name="Malas", slug="malas")
        for mukhi, origin, price in [(1, "Nepali", 18500), (2, "Nepali", 5500),
                                     (3, "Indonesian", 2800), (11, "Nepali", 6200)]:
            Product.objects.create(category=rudraksha, name=f"Astrol {mukhi} Mukhi Rudraksha",
                                   slug=f"rudraksha-{mukhi}", origin=origin, price=price)

    def test_home_shows_curated_products(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "store/home.html")
        self.assertEqual(len(response.context["featured_products"]), 4)

    def test_combined_filters_and_sort(self):
        response = self.client.get("/shop/", {"origin": "Nepali", "price": "3000-7000", "sort": "price-desc"})
        self.assertEqual([int(p.price) for p in response.context["products"]], [6200, 5500])
        self.assertContains(response, 'value="Nepali" checked')
        self.assertContains(response, 'value="price-desc" selected')

    def test_mukhi_one_does_not_match_eleven(self):
        response = self.client.get("/shop/", {"mukhi": "1"})
        self.assertEqual([p.slug for p in response.context["products"]], ["rudraksha-1"])

    def test_multiple_mukhis(self):
        response = self.client.get("/shop/", {"mukhi": ["1", "3"], "sort": "price-asc"})
        self.assertEqual([p.slug for p in response.context["products"]], ["rudraksha-3", "rudraksha-1"])

    def test_empty_category_uses_correct_heading(self):
        response = self.client.get("/shop/", {"category": "malas"})
        self.assertContains(response, "Malas Collection")
        self.assertContains(response, "No products found")

    def test_search_and_invalid_sort(self):
        response = self.client.get("/shop/", {"q": "Indonesian", "sort": "invalid"})
        self.assertEqual([p.slug for p in response.context["products"]], ["rudraksha-3"])


class FullCatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from .models import ProductVariant
        cls.bracelets = Category.objects.create(name="Bracelets", slug="bracelets")
        cls.dhan = Category.objects.create(name="Dhan Yog", slug="dhan-yog")
        cls.product = Product.objects.create(name="Pyrite Bracelet", slug="pyrite-bracelet", category=cls.bracelets, price=1000)
        cls.product.collections.add(cls.dhan)
        cls.standard = ProductVariant.objects.create(product=cls.product, source_id="v1", name="Standard", price=1000)
        cls.silver = ProductVariant.objects.create(product=cls.product, source_id="v2", name="Silver", price=1500)
        cls.sold = ProductVariant.objects.create(product=cls.product, source_id="v3", name="Large", price=2000, available=False)
        cls.sample = Product.objects.create(name="Sample Ring", slug="sample-ring", category=cls.bracelets, price=3500, is_sample=True, available=False)

    def test_global_search_and_secondary_collection(self):
        response = self.client.get('/shop/', {'q': 'Pyrite'})
        self.assertEqual(response.context['product_count'], 1)
        response = self.client.get('/shop/', {'category': 'dhan-yog'})
        self.assertEqual(list(response.context['products']), [self.product])

    def test_pagination_preserves_filters(self):
        Product.objects.bulk_create([Product(name=f'Bracelet {n}', slug=f'bracelet-{n}', category=self.bracelets, price=100) for n in range(30)])
        response = self.client.get('/shop/', {'category': 'bracelets', 'sort': 'price-asc', 'page': 2})
        self.assertEqual(response.context['product_count'], 32)
        self.assertEqual(len(response.context['products']), 7)
        self.assertIn('sort=price-asc', response.context['page_query'])
        self.assertNotIn('page=', response.context['page_query'])

    def test_cart_uses_variant_price_and_keeps_options_separate(self):
        for variant in (self.standard, self.silver, self.silver):
            response = self.client.post(f'/cart/add/{self.product.pk}/', {'variant': variant.pk, 'price': '1'})
            self.assertEqual(response.status_code, 302)
        response = self.client.get('/cart/')
        self.assertEqual(response.context['total'], 4000)
        self.assertEqual(len(response.context['items']), 2)
        self.assertContains(response, 'Silver')
        key = f'{self.product.pk}:{self.silver.pk}'
        self.client.post(f'/cart/remove/{key}/')
        self.assertEqual(self.client.get('/cart/').context['total'], 1000)

    def test_samples_and_unavailable_options_cannot_be_purchased(self):
        self.assertEqual(self.client.post(f'/cart/add/{self.sample.pk}/').status_code, 400)
        self.assertEqual(self.client.post(f'/cart/add/{self.product.pk}/', {'variant': self.sold.pk}).status_code, 400)
        self.assertEqual(self.client.post(f'/cart/add/{self.product.pk}/', {'variant': 'invalid'}).status_code, 400)
        self.assertEqual(self.client.get(f'/cart/add/{self.product.pk}/').status_code, 405)

    def test_variant_required_and_external_redirect_rejected(self):
        response = self.client.post(f'/cart/add/{self.product.pk}/')
        self.assertRedirects(response, self.product.get_absolute_url())
        response = self.client.post(f'/cart/add/{self.product.pk}/', {'variant': self.standard.pk, 'next': 'https://example.com'})
        self.assertRedirects(response, '/cart/')

    def test_cart_mutations_require_csrf(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(f'/cart/add/{self.product.pk}/', {'variant': self.standard.pk}).status_code, 403)

    def test_sample_detail_and_availability_filter(self):
        response = self.client.get(self.sample.get_absolute_url())
        self.assertContains(response, 'Sample — not for sale')
        self.assertNotContains(response, 'class="detail-purchase"')
        response = self.client.get('/shop/', {'availability': 'available'})
        self.assertEqual(list(response.context['products']), [self.product])

    def test_import_is_repeatable_and_preserves_edits(self):
        import json
        from io import StringIO
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from django.core.management import call_command
        from .models import ProductVariant
        row = {'source_id': 'reference-1', 'name': 'Reference Bracelet', 'category': 'bracelets',
               'origin': '', 'image': 'images/products/bracelet.png', 'source_url': 'https://rudradhyay.com/products/example',
               'dhan_yog': True, 'variants': [{'source_id': 'import-v1', 'name': 'Standard', 'price': '800', 'compare_at_price': None, 'available': True, 'sku': None}]}
        with TemporaryDirectory() as folder:
            path = Path(folder)/'catalog.json'
            path.write_text(json.dumps({'products': [row]}))
            call_command('import_reference_catalog', catalog=path, stdout=StringIO())
            imported = Product.objects.get(source_id='reference-1')
            imported.price = 900
            imported.save()
            count = Product.objects.count()
            call_command('import_reference_catalog', catalog=path, stdout=StringIO())
            self.assertEqual(Product.objects.count(), count)
            self.assertEqual(Product.objects.get(source_id='reference-1').price, 900)
            self.assertEqual(ProductVariant.objects.filter(source_id='import-v1').count(), 1)


class HomepageTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Bracelets', slug='bracelets')
        self.available = Product.objects.create(name='Available Bracelet', slug='available-bracelet', category=self.category, price=500)
        Product.objects.create(name='Sample Bracelet', slug='sample-bracelet', category=self.category, price=100, is_sample=True)
        Product.objects.create(name='Sold Bracelet', slug='sold-bracelet', category=self.category, price=100, available=False)
        Product.objects.create(name='Hidden Bracelet', slug='hidden-bracelet', category=self.category, price=100, active=False)

    def test_homepage_only_promotes_purchasable_products(self):
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'store/home.html')
        self.assertEqual(response.context['featured_products'], [self.available])
        self.assertEqual(response.context['home_collections'][0]['product'], self.available)
        self.assertContains(response, 'A little closer')

    def test_featured_collection_and_unknown_selection(self):
        response = self.client.get('/', {'edit': 'bracelets'})
        self.assertEqual(response.context['featured_products'], [self.available])
        self.assertEqual(response.context['selected_edit'], 'bracelets')
        self.assertEqual(self.client.get('/', {'edit': 'unknown'}).context['selected_edit'], 'curated')

    def test_homepage_handles_empty_inventory(self):
        Product.objects.all().delete()
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A new selection is on its way.')


class FilterRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rudraksha = Category.objects.create(name='Rudraksha', slug='rudraksha')
        cls.bracelets = Category.objects.create(name='Bracelets', slug='bracelets')
        cls.dhan = Category.objects.create(name='Dhan Yog', slug='dhan-yog')
        rows = [
            ('1 Mukhi Rudraksha', 'one', 'Nepali', 3000, cls.rudraksha),
            ('11 Mukhi Rudraksha', 'eleven', 'Nepali', 7000, cls.rudraksha),
            ('21 Face Rudraksha', 'twenty-one', 'Indonesian', 7001, cls.rudraksha),
            ('7 Mukhi Bracelet', 'seven-bracelet', 'Nepali', 2999, cls.bracelets),
            ('Crystal Bracelet', 'crystal', '', 1000, cls.bracelets),
        ]
        for name, slug, origin, price, category in rows:
            Product.objects.create(name=name, slug=slug, origin=origin, price=price, category=category)
        Product.objects.get(slug='seven-bracelet').collections.add(cls.dhan)
        Product.objects.create(name='Sold Bracelet', slug='sold', category=cls.bracelets, price=2000, available=False)
        Product.objects.create(name='Sample Bracelet', slug='sample', category=cls.bracelets, price=500, is_sample=True, available=False)
        Product.objects.create(name='No Price', slug='no-price', category=cls.bracelets, price=0)

    def slugs(self, **params):
        return {p.slug for p in self.client.get('/shop/', params).context['products']}

    def test_every_price_boundary_and_unpriced_product(self):
        self.assertEqual(self.slugs(price='3000-7000'), {'one', 'eleven'})
        self.assertEqual(self.slugs(price='over-7000'), {'twenty-one'})
        self.assertEqual(self.slugs(price='under-3000'), {'seven-bracelet', 'crystal', 'sold', 'sample'})

    def test_origin_and_mukhi_multi_selection(self):
        self.assertEqual(self.slugs(origin=['Nepali', 'Indonesian'], mukhi=['1', '21']), {'one', 'twenty-one'})
        self.assertEqual(self.slugs(origin='Nepali', mukhi='7', category='bracelets'), {'seven-bracelet'})

    def test_availability_states(self):
        self.assertEqual(self.slugs(availability='sold-out'), {'sold', 'no-price'})
        self.assertEqual(self.slugs(availability='sample'), {'sample'})
        self.assertEqual(self.slugs(category='bracelets', availability='available'), {'seven-bracelet', 'crystal'})

    def test_secondary_collection_combines_with_other_filters(self):
        self.assertEqual(self.slugs(category='dhan-yog', origin='Nepali', price='under-3000', mukhi='7', availability='available'), {'seven-bracelet'})

    def test_chips_remove_only_one_filter(self):
        response = self.client.get('/shop/', {'category': 'bracelets', 'origin': ['Nepali', 'Indonesian'], 'mukhi': ['1', '7'], 'sort': 'price-desc', 'q': 'Bracelet', 'page': '2'})
        from urllib.parse import urlsplit, parse_qs
        chip = next(chip for chip in response.context['active_filters'] if chip['label'] == 'Nepali')
        params = parse_qs(urlsplit(chip['url']).query)
        self.assertEqual(params['origin'], ['Indonesian'])
        self.assertEqual(params['mukhi'], ['1', '7'])
        self.assertEqual(params['category'], ['bracelets'])
        self.assertEqual(params['sort'], ['price-desc'])
        self.assertEqual(params['q'], ['Bracelet'])
        self.assertNotIn('page', params)

    def test_all_products_exposes_mukhi_and_single_form_sorting(self):
        response = self.client.get('/shop/')
        self.assertContains(response, 'value="21"')
        self.assertContains(response, 'form="collection-filters"')
        self.assertNotContains(response, 'id="sort-form"')

    def test_impossible_combination_keeps_selections_visible(self):
        response = self.client.get('/shop/', {'category': 'bracelets', 'origin': 'Indonesian', 'availability': 'available'})
        self.assertEqual(response.context['product_count'], 0)
        self.assertContains(response, 'value="Indonesian" checked')
        self.assertContains(response, 'No products match this combination')

    def test_invalid_values_fall_back_to_unfiltered_state(self):
        response = self.client.get('/shop/', {'category': 'bad', 'origin': 'bad', 'price': 'bad', 'availability': 'bad', 'sort': 'bad', 'mukhi': '99'})
        self.assertEqual(response.context['product_count'], 8)
        self.assertEqual(response.context['active_filters'], [])
        self.assertEqual(response.context['sort'], 'featured')


class InventoryPortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        cls.owner = get_user_model().objects.create_superuser(username='inventory-owner', password='test-password-only')
        cls.customer = get_user_model().objects.create_user(username='shopper', password='test-password-only')
        cls.staff = get_user_model().objects.create_user(username='limited-staff', password='test-password-only', is_staff=True)
        cls.category = Category.objects.create(name='Malas', slug='malas')
        cls.product = Product.objects.create(name='Inventory Mala', slug='inventory-mala', category=cls.category, price=500, stock_quantity=2)

    def test_admin_requires_staff_and_model_permissions(self):
        self.assertEqual(self.client.get('/admin/').status_code, 302)
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get('/admin/').status_code, 302)
        self.assertEqual(self.client.get('/admin/store/product/').status_code, 302)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get('/admin/store/product/').status_code, 403)
        self.client.force_login(self.owner)
        for url in ['/admin/', '/admin/store/product/', '/admin/store/productvariant/', '/admin/store/category/', '/admin/store/product/add/']:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertContains(self.client.get('/admin/'), 'Welcome to your inventory.')

    def test_zero_stock_updates_storefront_and_filters(self):
        self.product.stock_quantity = 0
        self.product.save()
        self.assertFalse(self.product.can_purchase)
        self.assertNotIn(self.product, Product.objects.purchasable())
        response = self.client.get('/shop/', {'availability': 'available'})
        self.assertEqual(response.context['product_count'], 0)
        self.assertContains(self.client.get(self.product.get_absolute_url()), 'Currently unavailable')
        self.assertEqual(self.client.post(f'/cart/add/{self.product.pk}/').status_code, 400)

    def test_cart_limits_quantity_without_deducting_stock(self):
        for _ in range(3):
            self.client.post(f'/cart/add/{self.product.pk}/')
        self.assertEqual(self.client.session['cart'][str(self.product.pk)], 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 2)
        self.product.stock_quantity = 1
        self.product.save()
        response = self.client.get('/cart/')
        self.assertEqual(response.context['items'][0]['qty'], 1)
        self.assertEqual(response.context['total'], 500)

    def test_variant_stock_and_price_sync(self):
        from .models import ProductVariant
        sold = ProductVariant.objects.create(product=self.product, name='Small', price=300, stock_quantity=0)
        available = ProductVariant.objects.create(product=self.product, name='Large', price=700, stock_quantity=1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, 700)
        self.assertTrue(self.product.can_purchase)
        for _ in range(2):
            self.client.post(f'/cart/add/{self.product.pk}/', {'variant': available.pk})
        self.assertEqual(self.client.session['cart'][f'{self.product.pk}:{available.pk}'], 1)
        self.assertEqual(self.client.post(f'/cart/add/{self.product.pk}/', {'variant': sold.pk}).status_code, 400)
        available.stock_quantity = 0
        available.save()
        self.product.refresh_from_db()
        self.assertFalse(self.product.can_purchase)
        self.assertNotIn(self.product, Product.objects.purchasable())
        self.assertEqual(self.client.get('/cart/').context['items'], [])
        sold.stock_quantity = 3
        sold.price = 450
        sold.save()
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, 450)
        self.assertIn(self.product, Product.objects.purchasable())

    def test_unknown_stock_is_preserved_and_samples_stay_blocked(self):
        self.product.stock_quantity = None
        self.product.save()
        self.assertTrue(self.product.can_purchase)
        self.product.is_sample = True
        self.product.save()
        self.assertFalse(self.product.can_purchase)
        self.assertNotIn(self.product, Product.objects.purchasable())

    def test_stock_and_price_validate_nonnegative(self):
        from django.core.exceptions import ValidationError
        self.product.stock_quantity = -1
        self.product.price = -1
        with self.assertRaises(ValidationError) as result:
            self.product.full_clean()
        self.assertIn('stock_quantity', result.exception.message_dict)
        self.assertIn('price', result.exception.message_dict)

    def test_admin_can_create_product_with_uploaded_photo(self):
        from io import BytesIO
        from tempfile import TemporaryDirectory
        from django.test import override_settings
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image
        buffer = BytesIO()
        Image.new('RGB', (8, 8), 'brown').save(buffer, 'PNG')
        self.client.force_login(self.owner)
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            response = self.client.post('/admin/store/product/add/', {
                'name': 'Uploaded Mala', 'slug': 'uploaded-mala', 'category': self.category.pk,
                'price': '600', 'stock_quantity': '4', 'available': 'on', 'active': 'on',
                'uploaded_image': SimpleUploadedFile('mala.png', buffer.getvalue(), content_type='image/png'),
                'variants-TOTAL_FORMS': '0', 'variants-INITIAL_FORMS': '0',
                'variants-MIN_NUM_FORMS': '0', 'variants-MAX_NUM_FORMS': '1000', '_save': 'Save',
            })
            self.assertEqual(response.status_code, 302)
            product = Product.objects.get(slug='uploaded-mala')
            self.assertTrue(product.image_url.startswith('/media/products/'))
            self.assertEqual(product.stock_quantity, 4)
            self.assertContains(self.client.get(product.get_absolute_url()), product.image_url)
