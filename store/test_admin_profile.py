from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, TestCase

from .models import CustomerProfile, StaffProfile


class AdminProfileTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username='staff', email='staff@example.com', password='Cedar!Meadow8742', is_staff=True)
        self.client.force_login(self.staff)

    def test_staff_can_edit_own_details_without_user_edit_permission(self):
        response = self.client.post('/admin/profile/', {
            'first_name': 'Rahul', 'last_name': 'Pearson', 'email': 'RAHUL@example.com', 'phone': '+91 9876543210',
            'is_superuser': 'on', 'is_active': '', 'username': 'changed', 'user_permissions': '1',
        })
        self.assertRedirects(response, '/admin/profile/')
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.get_full_name(), 'Rahul Pearson')
        self.assertEqual(self.staff.email, 'rahul@example.com')
        self.assertEqual(self.staff.username, 'staff')
        self.assertFalse(self.staff.is_superuser)
        self.assertTrue(self.staff.is_active)
        self.assertFalse(self.staff.user_permissions.exists())
        self.assertEqual(StaffProfile.objects.get(user=self.staff).phone, '+91 9876543210')
        self.assertEqual(CustomerProfile.objects.get(user=self.staff).phone, '')
        self.assertContains(self.client.get('/admin/profile/'), '+91 9876543210')

    def test_permissions_include_groups_and_direct_assignments(self):
        group = Group.objects.create(name='Catalog team')
        group.permissions.add(Permission.objects.get(codename='view_product'))
        self.staff.groups.add(group)
        self.staff.user_permissions.add(Permission.objects.get(codename='change_product'))
        response = self.client.get('/admin/profile/')
        self.assertContains(response, 'Catalog team')
        self.assertContains(response, 'Can view product')
        self.assertContains(response, 'Can change product')
        self.assertNotContains(response, 'Can delete product')

    def test_superuser_sees_full_access_and_profile_link(self):
        self.staff.is_superuser = True
        self.staff.save()
        response = self.client.get('/admin/profile/')
        self.assertContains(response, 'Super administrator · Full access')
        self.assertContains(self.client.get('/admin/'), 'href="/admin/profile/"')

    def test_invalid_phone_and_duplicate_email_do_not_save(self):
        get_user_model().objects.create_user(username='other', email='other@example.com')
        response = self.client.post('/admin/profile/', {'first_name': 'Changed', 'email': 'OTHER@example.com', 'phone': 'abc'})
        self.assertIn('phone', response.context['form'].errors)
        self.assertIn('email', response.context['form'].errors)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.first_name, '')
        self.assertEqual(self.staff.email, 'staff@example.com')
        self.assertFalse(StaffProfile.objects.exists())

    def test_post_cannot_target_another_user(self):
        other = get_user_model().objects.create_user(username='other', email='other@example.com')
        self.client.post('/admin/profile/', {'first_name': 'Mine', 'email': 'staff@example.com', 'user': other.pk, 'id': other.pk})
        other.refresh_from_db()
        self.assertEqual(other.first_name, '')
        self.assertEqual(other.email, 'other@example.com')

    def test_anonymous_customer_and_inactive_staff_cannot_access(self):
        self.client.logout()
        self.assertRedirects(self.client.get('/admin/profile/'), '/admin/login/?next=/admin/profile/')
        customer = get_user_model().objects.create_user(username='customer')
        self.client.force_login(customer)
        response = self.client.post('/admin/profile/', {'first_name': 'Unauthorized'})
        self.assertEqual(response.status_code, 302)
        customer.refresh_from_db()
        self.assertEqual(customer.first_name, '')
        self.staff.is_active = False
        self.staff.save()
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get('/admin/profile/').status_code, 302)

    def test_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.staff)
        self.assertEqual(client.post('/admin/profile/', {'email': 'staff@example.com'}).status_code, 403)
