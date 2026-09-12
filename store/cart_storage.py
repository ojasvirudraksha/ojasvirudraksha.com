"""Persistent customer carts, with session storage for guests."""
from contextlib import contextmanager
from functools import wraps

from django.db import transaction

from .models import CustomerProfile


@contextmanager
def locked_cart(user):
    with transaction.atomic():
        CustomerProfile.objects.get_or_create(user=user)
        profile = CustomerProfile.objects.select_for_update().get(user=user)
        yield profile
        profile.save(update_fields=['cart'])


def get_cart(request):
    if getattr(request, '_cart_loaded', False):
        return request.session.get('cart', {})
    if request.user.is_authenticated:
        profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
        return profile.cart
    return request.session.get('cart', {})


def persistent_cart(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return view(request, *args, **kwargs)
        with locked_cart(request.user) as profile:
            if 'cart_owner' not in request.session and not profile.cart:
                profile.cart = request.session.get('cart', {}).copy()
            request._cart_loaded = True
            request.session['cart_owner'] = request.user.pk
            request.session['cart'] = profile.cart.copy()
            response = view(request, *args, **kwargs)
            profile.cart = request.session.get('cart', {})
            return response
    return wrapped
