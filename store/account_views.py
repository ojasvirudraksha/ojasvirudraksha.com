import hashlib
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from .account_forms import CustomerSignupForm, CustomerLoginForm, CustomerProfileForm, CustomerAddressForm
from .models import CustomerProfile, CustomerAddress, Product, WishlistItem


def attempt_key(request):
    # Hash the local IP; never trust an arbitrary forwarded-address header.
    return 'customer-auth:' + hashlib.sha256(request.META.get('REMOTE_ADDR', '').encode()).hexdigest()


def record_failure(request):
    key = attempt_key(request)
    cache.set(key, cache.get(key, 0) + 1, 900)


def safe_next(request):
    target = request.POST.get('next') or request.GET.get('next') or '/account/'
    return target if url_has_allowed_host_and_scheme(target, {request.get_host()}, require_https=request.is_secure()) else '/account/'


class CustomerLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = CustomerLoginForm
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        if cache.get(attempt_key(request), 0) >= 10:
            form = self.get_form()
            form.add_error(None, 'Too many attempts. Please try again in 15 minutes.')
            return self.render_to_response(self.get_context_data(form=form), status=429)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        record_failure(self.request)
        return super().form_invalid(form)

    def form_valid(self, form):
        response = super().form_valid(form)
        CustomerProfile.objects.get_or_create(user=self.request.user)
        self.request.session.set_expiry(60 * 60 * 24 * 14 if form.cleaned_data['remember_me'] else 0)
        cache.delete(attempt_key(self.request))
        return response


@never_cache
def signup(request):
    if request.user.is_authenticated:
        return redirect('account_dashboard')
    form = CustomerSignupForm(request.POST or None)
    if request.method == 'POST':
        if cache.get(attempt_key(request), 0) >= 10:
            form.add_error(None, 'Too many attempts. Please try again in 15 minutes.')
            return render(request, 'accounts/signup.html', {'form': form, 'next': safe_next(request)}, status=429)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
            except IntegrityError:
                form.add_error('email', 'This email is already registered. Please sign in.')
            else:
                login(request, user)
                request.session.set_expiry(0)
                messages.success(request, 'Welcome to ASTROL. Your account is ready.')
                return redirect(safe_next(request))
        record_failure(request)
    return render(request, 'accounts/signup.html', {'form': form, 'next': safe_next(request)})


@never_cache
@login_required
def dashboard(request):
    return render(request, 'accounts/dashboard.html', {'account_tab': 'overview', 'address_count': request.user.addresses.count(),
                  'wishlist_total': request.user.wishlist_items.filter(product__active=True).count(),
                  'default_address': request.user.addresses.filter(is_default=True).first()})


@never_cache
@login_required
def profile(request):
    customer, _ = CustomerProfile.objects.get_or_create(user=request.user)
    form = CustomerProfileForm(request.POST or None, initial={'first_name': request.user.first_name, 'last_name': request.user.last_name, 'phone': customer.phone})
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.save(update_fields=['first_name', 'last_name'])
            customer.phone = form.cleaned_data['phone']
            customer.save()
        messages.success(request, 'Your profile has been updated.')
        return redirect('account_profile')
    return render(request, 'accounts/profile.html', {'form': form, 'account_tab': 'profile'})


@never_cache
@login_required
def addresses(request):
    return render(request, 'accounts/addresses.html', {'addresses': request.user.addresses.all(), 'account_tab': 'addresses'})


@never_cache
@login_required
def address_edit(request, pk=None):
    address = get_object_or_404(CustomerAddress, pk=pk, user=request.user) if pk else CustomerAddress(user=request.user)
    form = CustomerAddressForm(request.POST or None, instance=address)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            address = form.save(commit=False)
            address.user = request.user
            if not request.user.addresses.exclude(pk=address.pk).exists():
                address.is_default = True
            if address.is_default:
                request.user.addresses.exclude(pk=address.pk).update(is_default=False)
            address.save()
        messages.success(request, 'Your address has been saved.')
        return redirect('account_addresses')
    return render(request, 'accounts/address_form.html', {'form': form, 'editing': bool(pk), 'account_tab': 'addresses'})


@never_cache
@login_required
@require_POST
def address_delete(request, pk):
    with transaction.atomic():
        address = get_object_or_404(CustomerAddress, pk=pk, user=request.user)
        was_default = address.is_default
        address.delete()
        replacement = request.user.addresses.first() if was_default else None
        if replacement:
            replacement.is_default = True
            replacement.save(update_fields=['is_default'])
    messages.success(request, 'The address has been removed.')
    return redirect('account_addresses')


@never_cache
@login_required
def wishlist(request):
    products = Product.objects.filter(active=True, saved_by__user=request.user).select_related('category').prefetch_related('variants').order_by('-saved_by__created_at')
    return render(request, 'accounts/wishlist.html', {'products': products, 'account_tab': 'wishlist'})


def wishlist_data(user):
    return {str(item.product_id): {'name': item.product.name, 'url': item.product.get_absolute_url()}
            for item in WishlistItem.objects.filter(user=user, product__active=True).select_related('product')}


@never_cache
@login_required
@require_POST
def wishlist_update(request):
    action = request.POST.get('action')
    if action == 'merge':
        ids = [int(value) for value in request.POST.getlist('ids')[:100] if value.isdigit() and len(value) < 15]
        WishlistItem.objects.bulk_create([WishlistItem(user=request.user, product=p) for p in Product.objects.filter(pk__in=ids, active=True)], ignore_conflicts=True)
    elif action in ('add', 'remove'):
        value = request.POST.get('product', '')
        if not value.isdigit() or len(value) > 14:
            return JsonResponse({'error': 'Invalid product.'}, status=400)
        product = get_object_or_404(Product, pk=int(value), active=True)
        if action == 'add':
            WishlistItem.objects.get_or_create(user=request.user, product=product)
        else:
            WishlistItem.objects.filter(user=request.user, product=product).delete()
    else:
        return JsonResponse({'error': 'Invalid wishlist action.'}, status=400)
    return JsonResponse({'items': wishlist_data(request.user)})


@never_cache
@login_required
def orders(request):
    return render(request, 'accounts/orders.html', {'account_tab': 'orders'})
