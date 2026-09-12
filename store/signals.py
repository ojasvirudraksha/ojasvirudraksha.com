from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import ProductVariant
from .cart_storage import locked_cart


@receiver(post_save, sender=ProductVariant)
@receiver(post_delete, sender=ProductVariant)
def update_product_starting_price(sender, instance, **kwargs):
    # Use a fresh relation so prefetched admin objects cannot leave stale prices.
    from .models import Product
    product = Product.objects.filter(pk=instance.product_id).first()
    if product:
        product.refresh_variant_price()


@receiver(user_logged_in)
def restore_customer_cart(sender, request, user, **kwargs):
    if request is None:
        return
    with locked_cart(user) as profile:
        guest_cart = request.session.get('cart', {}) if 'cart_owner' not in request.session else {}
        for key, quantity in guest_cart.items():
            if isinstance(quantity, int) and quantity > 0:
                profile.cart[key] = profile.cart.get(key, 0) + quantity
        request.session['cart_owner'] = user.pk
        request.session['cart'] = profile.cart.copy()


@receiver(user_logged_out)
def preserve_legacy_cart(sender, request, user, **kwargs):
    # Preserve carts in sessions created before database persistence was deployed.
    if request is not None and user is not None and user.is_authenticated:
        with locked_cart(user) as profile:
            if not profile.cart and 'cart_owner' not in request.session and 'cart' in request.session:
                profile.cart = request.session['cart'].copy()
