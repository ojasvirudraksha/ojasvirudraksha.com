import re
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm
from django.db.models import Q
from .models import CustomerAddress, CustomerProfile


def clean_phone(value):
    value = value.strip()
    if value and (not re.fullmatch(r'[+0-9 ()-]+', value) or not 7 <= len(re.sub(r'\D', '', value)) <= 15):
        raise forms.ValidationError('Enter a valid phone number with 7–15 digits.')
    return value


class CustomerSignupForm(UserCreationForm):
    first_name = forms.CharField(label='First name', max_length=150, widget=forms.TextInput(attrs={'autocomplete': 'given-name'}))
    last_name = forms.CharField(label='Last name', max_length=150, required=False, widget=forms.TextInput(attrs={'autocomplete': 'family-name'}))
    email = forms.EmailField(max_length=150, widget=forms.EmailInput(attrs={'autocomplete': 'email'}))
    phone = forms.CharField(label='Phone number', max_length=25, required=False,
                           help_text='Optional. Include your country code, for example +91.',
                           widget=forms.TextInput(attrs={'autocomplete': 'tel', 'type': 'tel'}))

    class Meta:
        model = get_user_model()
        fields = ('first_name', 'last_name', 'email', 'phone', 'password1', 'password2')

    def clean_phone(self):
        return clean_phone(self.cleaned_data['phone'])

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if get_user_model().objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).exists():
            raise forms.ValidationError('An account with this email already exists. Sign in or reset your password.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
            CustomerProfile.objects.update_or_create(user=user, defaults={'phone': self.cleaned_data['phone']})
        return user


class AdminPasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        return (user for user in super().get_users(email) if user.is_staff)


class CustomerLoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email address', max_length=150, widget=forms.EmailInput(attrs={'autocomplete': 'username'}))
    remember_me = forms.BooleanField(required=False, label='Keep me signed in')

    def clean_username(self):
        return self.cleaned_data['username'].strip().lower()

    def confirm_login_allowed(self, user):
        if user.is_staff or user.is_superuser:
            raise forms.ValidationError('Use the admin portal for staff accounts.')
        super().confirm_login_allowed(user)


class CustomerProfileForm(forms.Form):
    first_name = forms.CharField(label='First name', max_length=150)
    last_name = forms.CharField(label='Last name', max_length=150, required=False)
    phone = forms.CharField(label='Phone number', max_length=25, required=False, widget=forms.TextInput(attrs={'autocomplete': 'tel', 'type': 'tel'}))

    def clean_phone(self):
        return clean_phone(self.cleaned_data['phone'])


class CustomerAddressForm(forms.ModelForm):
    class Meta:
        model = CustomerAddress
        fields = ('label', 'full_name', 'phone', 'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country', 'is_default')
        labels = {'is_default': 'Use as my default address'}
        widgets = {'phone': forms.TextInput(attrs={'autocomplete': 'tel', 'type': 'tel'}),
                   'full_name': forms.TextInput(attrs={'autocomplete': 'name'}),
                   'address_line1': forms.TextInput(attrs={'autocomplete': 'address-line1'}),
                   'address_line2': forms.TextInput(attrs={'autocomplete': 'address-line2'}),
                   'city': forms.TextInput(attrs={'autocomplete': 'address-level2'}),
                   'state': forms.TextInput(attrs={'autocomplete': 'address-level1'}),
                   'postal_code': forms.TextInput(attrs={'autocomplete': 'postal-code'})}

    def clean_phone(self):
        return clean_phone(self.cleaned_data['phone'])
