from django.db.models import Case, IntegerField, Q, Value, When
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .currency import format_money, market
from .models import Product


@require_GET
def product_suggestions(request):
    query = ' '.join(request.GET.get('q', '').split())[:100]
    if not query:
        return JsonResponse({'query': '', 'results': [], 'count': 0})
    products = Product.objects.filter(active=True)
    for word in query.split()[:8]:
        products = products.filter(Q(name__icontains=word) | Q(category__name__icontains=word) | Q(origin__icontains=word))
    count = products.count()
    products = products.annotate(search_rank=Case(
        When(name__iexact=query, then=Value(0)),
        When(name__istartswith=query, then=Value(1)),
        default=Value(2), output_field=IntegerField(),
    )).select_related('category').prefetch_related('variants').order_by('search_rank', 'is_sample', '-available', 'name', 'id')[:8]
    current = market(request)
    results = [{
        'id': product.pk, 'name': product.name, 'url': product.get_absolute_url(),
        'image': product.image_url, 'category': product.category.name,
        'price': format_money(product.price, current) if product.price > 0 else 'Price unavailable',
        'price_prefix': 'Sample price' if product.is_sample else ('From' if product.has_options else ''),
        'badge': 'Sample' if product.is_sample else ('Sold out' if not product.can_purchase else ''),
    } for product in products]
    response = JsonResponse({'query': query, 'results': results, 'count': count})
    response['Cache-Control'] = 'private, no-store'
    return response
