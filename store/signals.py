from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import ProductVariant


@receiver(post_save, sender=ProductVariant)
@receiver(post_delete, sender=ProductVariant)
def update_product_starting_price(sender, instance, **kwargs):
    # Use a fresh relation so prefetched admin objects cannot leave stale prices.
    from .models import Product
    product = Product.objects.filter(pk=instance.product_id).first()
    if product:
        product.refresh_variant_price()
