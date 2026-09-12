"""Homepage merchandising using existing products and local photographs."""
from django.db.models import Q
from .models import Category, Product

COLLECTIONS = [
    ('rudraksha', 'Rudraksha', 'Sacred beginnings', None, 'astrol-7-mukhi-rudraksha'),
    ('malas', 'Malas', 'A moment of stillness', '9265956094181', None),
    ('bracelets', 'Bracelets', 'Meaning, worn daily', '9265111826661', None),
    ('tulsi-mala', 'Tulsi Mala', 'Rooted in devotion', '3883149099086', None),
    ('pearls', 'Pearls', 'Quiet elegance', '3881847291982', None),
    ('dhan-yog', 'Dhan Yog', 'Traditions of prosperity', '8336111337701', None),
]
EDITS = [('curated', 'Our selection'), ('rudraksha', 'Rudraksha'), ('malas', 'Malas'), ('bracelets', 'Bracelets')]


def home_context(request):
    available = Product.objects.purchasable().select_related('category').prefetch_related('variants')
    sources = [row[3] for row in COLLECTIONS if row[3]]
    slugs = [row[4] for row in COLLECTIONS if row[4]]
    preferred = list(available.filter(Q(source_id__in=sources) | Q(slug__in=slugs)))
    by_source = {p.source_id: p for p in preferred if p.source_id}
    by_slug = {p.slug: p for p in preferred}
    categories = {c.slug: c for c in Category.objects.all()}
    collections = []
    for slug, name, subtitle, source_id, product_slug in COLLECTIONS:
        if slug not in categories:
            continue
        product = by_source.get(source_id) if source_id else by_slug.get(product_slug)
        if product is None:
            product = available.filter(Q(category__slug=slug) | Q(collections__slug=slug)).distinct().order_by('-featured', 'id').first()
        if product is not None:
            collections.append({'slug': slug, 'name': name, 'subtitle': subtitle, 'product': product})
    selected_edit = request.GET.get('edit', 'curated')
    if selected_edit not in dict(EDITS):
        selected_edit = 'curated'
    if selected_edit == 'curated':
        products = list({c['product'].pk: c['product'] for c in collections}.values())[:5]
        if len(products) < 5:
            products += list(available.exclude(pk__in=[p.pk for p in products]).order_by('-featured', 'id')[:5-len(products)])
    else:
        products = list(available.filter(category__slug=selected_edit).order_by('-featured', 'price', 'id')[:5])
    return {'selected': 'home', 'home_collections': collections, 'featured_products': products,
            'home_edits': EDITS, 'selected_edit': selected_edit,
            'mala_feature': next((c['product'] for c in collections if c['slug'] == 'malas'), None),
            'bracelet_feature': next((c['product'] for c in collections if c['slug'] == 'bracelets'), None)}
