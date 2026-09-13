from django import forms
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.views.decorators.http import require_http_methods

from .account_forms import clean_phone
from .models import StaffProfile


class AdminProfileForm(forms.ModelForm):
    email = forms.EmailField(label='Email address', help_text='Used for password recovery. Your sign-in username stays the same.')
    phone = forms.CharField(label='Phone number', max_length=25, required=False,
                           help_text='Include your country code, for example +91.',
                           widget=forms.TextInput(attrs={'type': 'tel', 'autocomplete': 'tel'}))

    class Meta:
        model = get_user_model()
        fields = ('first_name', 'last_name', 'email', 'phone')
        widgets = {'first_name': forms.TextInput(attrs={'autocomplete': 'given-name'}),
                   'last_name': forms.TextInput(attrs={'autocomplete': 'family-name'})}

    def clean_phone(self):
        return clean_phone(self.cleaned_data['phone'])

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if get_user_model().objects.exclude(pk=self.instance.pk).filter(email__iexact=email).exists():
            raise forms.ValidationError('This email address is already used by another account.')
        return email


@require_http_methods(['GET', 'POST'])
def profile(request):
    user = request.user
    phone = StaffProfile.objects.filter(user=user).values_list('phone', flat=True).first() or ''
    form = AdminProfileForm(request.POST if request.method == 'POST' else None,
                            instance=user, initial={'phone': phone})
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            # Only personal details can be changed here, including for staff who
            # do not have permission to edit users in the main administration.
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save(update_fields=['first_name', 'last_name', 'email'])
            StaffProfile.objects.update_or_create(user=user, defaults={'phone': form.cleaned_data['phone']})
        messages.success(request, 'Your profile has been updated.')
        return redirect('admin_profile')

    permissions = Permission.objects.none()
    if not user.is_superuser:
        permissions = Permission.objects.filter(Q(user=user) | Q(group__user=user)).select_related('content_type').distinct().order_by('content_type__app_label', 'content_type__model', 'name')
    return TemplateResponse(request, 'admin/profile.html', {
        **admin.site.each_context(request), 'title': 'My profile', 'form': form,
        'profile_user': user, 'groups': user.groups.order_by('name'),
        'profile_permissions': permissions,
    })
