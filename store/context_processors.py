from .models import Category
from .cart_storage import get_cart


def cart_count(request):
    cart = get_cart(request)
    return {"cart_count": sum(qty for qty in cart.values() if isinstance(qty, int) and qty > 0),
            "nav_categories": Category.objects.all()}


def admin_inventory(request):
    if request.path != '/admin/' or not request.user.has_perm('store.view_product'):
        return {}
    from django.db.models import Q
    from .models import Product
    products = Product.objects.all()
    low = Q(variants__isnull=True, stock_quantity__gte=1, stock_quantity__lte=5) | Q(variants__stock_quantity__gte=1, variants__stock_quantity__lte=5)
    untracked = Q(variants__isnull=True, stock_quantity__isnull=True) | Q(variants__isnull=False, variants__stock_quantity__isnull=True)
    return {'inventory_stats': {'products': products.count(), 'published': products.filter(active=True).count(),
                               'low_stock': products.filter(low).distinct().count(),
                               'untracked': products.filter(untracked).distinct().count()}}


def customer_account(request):
    if not request.user.is_authenticated or request.path.startswith('/admin/'):
        return {'customer_wishlist': {}}
    from .account_views import wishlist_data
    return {'customer_wishlist': wishlist_data(request.user)}
