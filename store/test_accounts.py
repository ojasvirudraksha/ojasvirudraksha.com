import re
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from .models import Category, CustomerAddress, CustomerProfile, Product, WishlistItem


class CustomerAccountTests(TestCase):
    def setUp(self):
        cache.clear()
        self.password = 'Cedar!Meadow8742'
        self.user = get_user_model().objects.create_user(username='river@example.com', email='river@example.com', password=self.password, first_name='River')
        self.other = get_user_model().objects.create_user(username='other@example.com', email='other@example.com', password=self.password)
        category = Category.objects.create(name='Malas', slug='malas')
        self.product = Product.objects.create(name='Test Mala', slug='test-mala', category=category, price=900)
        self.address_data = {'label': 'Home', 'full_name': 'River Singh', 'phone': '+91 9876543210', 'address_line1': '10 Garden Road', 'address_line2': '', 'city': 'Pune', 'state': 'Maharashtra', 'postal_code': '411001', 'country': 'India', 'is_default': 'on'}

    def test_signup_creates_normal_customer_and_keeps_cart(self):
        session = self.client.session
        session['cart'] = {str(self.product.pk): 1}
        session.save()
        response = self.client.post('/account/register/', {'first_name': 'Asha', 'last_name': 'Sharma', 'email': 'ASHA@example.com', 'password1': self.password, 'password2': self.password, 'is_staff': 'on', 'is_superuser': 'on', 'next': 'https://outside.example/'})
        self.assertRedirects(response, '/account/')
        user = get_user_model().objects.get(username='asha@example.com')
        self.assertTrue(user.check_password(self.password))
        self.assertNotEqual(user.password, self.password)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(CustomerProfile.objects.filter(user=user).exists())
        self.assertEqual(self.client.session['cart'], {str(self.product.pk): 1})
        self.assertEqual(self.client.get('/admin/').status_code, 302)

    def test_duplicate_email_and_weak_password_rejected(self):
        response = self.client.post('/account/register/', {'first_name': 'Other', 'email': 'RIVER@example.com', 'password1': '12345678', 'password2': '12345678'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('email', response.context['form'].errors)
        self.assertIn('password2', response.context['form'].errors)
        self.assertEqual(get_user_model().objects.count(), 2)

    def test_email_login_safe_next_and_post_only_logout(self):
        response = self.client.post('/account/login/?next=https://outside.example/', {'username': 'RIVER@EXAMPLE.COM', 'password': self.password})
        self.assertRedirects(response, '/account/')
        self.assertEqual(self.client.get('/account/logout/').status_code, 405)
        self.assertRedirects(self.client.post('/account/logout/'), '/account/login/')
        self.assertEqual(self.client.get('/account/profile/').status_code, 302)

    def test_login_throttles_repeated_failures(self):
        for _ in range(10):
            self.client.post('/account/login/', {'username': 'river@example.com', 'password': 'wrong'})
        response = self.client.post('/account/login/', {'username': 'river@example.com', 'password': 'wrong'})
        self.assertEqual(response.status_code, 429)

    def test_profile_updates_only_current_user(self):
        self.client.force_login(self.user)
        response = self.client.post('/account/profile/', {'first_name': 'River Updated', 'last_name': 'Singh', 'phone': '+91 9876543210', 'user': self.other.pk, 'is_staff': 'on'})
        self.assertRedirects(response, '/account/profile/')
        self.user.refresh_from_db()
        self.other.refresh_from_db()
        self.assertEqual(self.user.first_name, 'River Updated')
        self.assertEqual(self.other.first_name, '')
        self.assertFalse(self.user.is_staff)
        self.assertEqual(self.user.customer_profile.phone, '+91 9876543210')
        self.assertIn('no-store', self.client.get('/account/profile/')['Cache-Control'])

    def test_address_create_edit_default_and_delete(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.post('/account/addresses/add/', self.address_data), '/account/addresses/')
        first = self.user.addresses.get()
        data = dict(self.address_data, label='Work', address_line1='20 Office Road')
        self.assertRedirects(self.client.post('/account/addresses/add/', data), '/account/addresses/')
        second = self.user.addresses.get(label='Work')
        first.refresh_from_db()
        self.assertFalse(first.is_default)
        self.assertTrue(second.is_default)
        data['city'] = 'Mumbai'
        self.assertRedirects(self.client.post(f'/account/addresses/{second.pk}/edit/', data), '/account/addresses/')
        second.refresh_from_db()
        self.assertEqual(second.city, 'Mumbai')
        self.assertRedirects(self.client.post(f'/account/addresses/{second.pk}/delete/'), '/account/addresses/')
        first.refresh_from_db()
        self.assertTrue(first.is_default)

    def test_addresses_are_private_and_post_protected(self):
        foreign = CustomerAddress.objects.create(user=self.other, full_name='Other Customer', phone='9876543210', address_line1='Private Road', city='Pune', state='Maharashtra', postal_code='411001', country='India')
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(f'/account/addresses/{foreign.pk}/edit/').status_code, 404)
        self.assertEqual(self.client.post(f'/account/addresses/{foreign.pk}/delete/').status_code, 404)
        self.assertEqual(self.client.get(f'/account/addresses/{foreign.pk}/delete/').status_code, 405)
        self.assertTrue(CustomerAddress.objects.filter(pk=foreign.pk).exists())
        self.assertNotContains(self.client.get('/account/addresses/'), 'Private Road')

    def test_account_routes_require_login(self):
        for path in ['', 'profile/', 'addresses/', 'addresses/add/', 'wishlist/', 'orders/', 'password/']:
            self.assertEqual(self.client.get('/account/' + path).status_code, 302, path)

    def test_wishlist_merges_deduplicates_and_is_private(self):
        self.client.force_login(self.user)
        for _ in range(2):
            response = self.client.post('/account/wishlist/update/', {'action': 'merge', 'ids': [str(self.product.pk), 'invalid', str(self.product.pk), '999999']})
            self.assertEqual(response.status_code, 200)
        self.assertEqual(WishlistItem.objects.filter(user=self.user).count(), 1)
        self.assertContains(self.client.get('/account/wishlist/'), self.product.name)
        second_browser = Client()
        second_browser.force_login(self.user)
        self.assertContains(second_browser.get('/account/wishlist/'), self.product.name)
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get('/account/wishlist/'), self.product.name)
        self.client.post('/account/wishlist/update/', {'action': 'remove', 'product': self.product.pk})
        self.assertEqual(WishlistItem.objects.filter(user=self.user).count(), 1)
        self.client.force_login(self.user)
        self.client.post('/account/wishlist/update/', {'action': 'remove', 'product': self.product.pk})
        self.assertEqual(WishlistItem.objects.count(), 0)

    def test_account_writes_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post('/account/wishlist/update/', {'action': 'add', 'product': self.product.pk}).status_code, 403)
        self.assertEqual(client.post('/account/profile/', {'first_name': 'Changed'}).status_code, 403)

    def test_password_change_and_inactive_login(self):
        self.client.force_login(self.user)
        new_password = 'Maple!Garden9837'
        response = self.client.post('/account/password/', {'old_password': self.password, 'new_password1': new_password, 'new_password2': new_password})
        self.assertRedirects(response, '/account/password/changed/')
        self.assertEqual(self.client.get('/account/').status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))
        self.user.is_active = False
        self.user.save()
        self.client.logout()
        response = self.client.post('/account/login/', {'username': self.user.email, 'password': new_password})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_password_reset_token_flow(self):
        self.assertRedirects(self.client.post('/account/password/reset/', {'email': self.user.email}), '/account/password/reset/sent/')
        self.assertEqual(len(mail.outbox), 1)
        url = re.search(r'http://testserver(/account/password/reset/[^\s]+)', mail.outbox[0].body).group(1)
        redirect = self.client.get(url)
        self.assertEqual(redirect.status_code, 302)
        set_url = redirect.url
        new_password = 'Willow!Forest8432'
        self.assertRedirects(self.client.post(set_url, {'new_password1': new_password, 'new_password2': new_password}), '/account/password/reset/complete/')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'This link has expired')
        self.client.post('/account/password/reset/', {'email': 'unknown@example.com'})
        self.assertEqual(len(mail.outbox), 1)

    def test_customer_records_are_manageable_by_admin_only(self):
        profile = CustomerProfile.objects.create(user=self.user, phone='+91 9876543210')
        owner = get_user_model().objects.create_superuser(username='account-admin', password=self.password)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/admin/store/customerprofile/').status_code, 302)
        self.client.force_login(owner)
        for url in ['/admin/store/customerprofile/', f'/admin/store/customerprofile/{profile.pk}/change/', '/admin/store/customeraddress/', '/admin/store/wishlistitem/']:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertContains(self.client.get('/admin/store/customerprofile/'), self.user.email)
