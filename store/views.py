from decimal import Decimal
import re

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseBadRequest, QueryDict
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from .models import Product, ProductVariant, Category
from .currency import countries, market, format_money, convert


@require_POST
def set_country(request):
    code = request.POST.get('country', '')
    if code not in {c['code'] for c in countries()}:
        return HttpResponseBadRequest('Please select a valid country or region.')
    target = request.POST.get('next', '/')
    if not url_has_allowed_host_and_scheme(target, {request.get_host()}, require_https=request.is_secure()):
        target = '/'
    response = redirect(target or '/')
    response.set_cookie('astrol_country', code, max_age=365 * 86400, httponly=True, samesite='Lax', secure=request.is_secure())
    return response


def _catalog_context(request):
    categories = list(Category.objects.all())
    category_map = {c.slug: c for c in categories}
    category = request.GET.get("category", "all")
    if category not in category_map:
        category = "all"
    selected_category = category_map.get(category)
    all_products = Product.objects.filter(active=True).select_related("category").prefetch_related("variants")
    # Keep origin choices visible when switching collections, including zero-result combinations.
    origin_options = list(all_products.exclude(origin="").order_by("origin").values_list("origin", flat=True).distinct())
    origins = [origin for origin in origin_options if origin in request.GET.getlist("origin")]
    mukhis = [str(n) for n in range(1, 22) if str(n) in request.GET.getlist("mukhi")]
    q = request.GET.get("q", "").strip()
    current = market(request)
    low, high = format_money(3000, current), format_money(7000, current)
    price_labels = {"under-3000": f"Under {low}", "3000-7000": f"{low} – {high}", "over-7000": f"Above {high}"}
    availability_labels = {"available": "Available products", "sold-out": "Sold out", "sample": "Sample products"}
    ordering = {"featured": ("-featured", "is_sample", "-available", "id"), "price-asc": ("price", "id"),
                "price-desc": ("-price", "id"), "name": ("name", "id")}
    price = request.GET.get("price", "")
    price = price if price in price_labels else ""
    availability = request.GET.get("availability", "")
    availability = availability if availability in availability_labels else ""
    sort = request.GET.get("sort", "featured")
    sort = sort if sort in ordering else "featured"
    base = all_products
    if category != "all":
        base = base.filter(Q(category__slug=category) | Q(collections__slug=category)).distinct()
    qs = base
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(origin__icontains=q) | Q(category__name__icontains=q))
    if origins:
        qs = qs.filter(origin__in=origins)
    if mukhis:
        faces = Q()
        for mukhi in mukhis:
            faces |= Q(name__iregex=rf"(^|[^0-9]){mukhi}\s*(mukhi|face)")
        qs = qs.filter(faces)
    if price == "under-3000":
        qs = qs.filter(price__gt=0, price__lt=3000)
    elif price == "3000-7000":
        qs = qs.filter(price__gte=3000, price__lte=7000)
    elif price == "over-7000":
        qs = qs.filter(price__gt=7000)
    if availability == "available":
        qs = qs.purchasable()
    elif availability == "sold-out":
        qs = qs.filter(is_sample=False).exclude(pk__in=Product.objects.purchasable().values("pk"))
    elif availability == "sample":
        qs = qs.filter(is_sample=True)
    qs = qs.order_by(*ordering[sort])
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    params = QueryDict(mutable=True)
    params["category"] = category
    params["sort"] = sort
    for key, value in (("q", q), ("price", price), ("availability", availability)):
        if value:
            params[key] = value
    params.setlist("origin", origins)
    params.setlist("mukhi", mukhis)
    active_filters = []

    def add_chip(key, value, label):
        remaining = params.copy()
        values = [v for v in remaining.getlist(key) if v != value]
        if values:
            remaining.setlist(key, values)
        else:
            remaining.pop(key, None)
        active_filters.append({"label": label, "url": "/shop/?" + remaining.urlencode() + "#main-content"})

    if category != "all":
        add_chip("category", category, selected_category.name)
    if q:
        add_chip("q", q, f'Search: {q}')
    for origin in origins:
        add_chip("origin", origin, origin)
    for mukhi in mukhis:
        add_chip("mukhi", mukhi, f"{mukhi} Mukhi")
    if price:
        add_chip("price", price, price_labels[price])
    if availability:
        add_chip("availability", availability, availability_labels[availability])
    cover = base.filter(is_sample=False).order_by("-available", "id").first()
    return {"products": page.object_list, "page_obj": page, "product_count": page.paginator.count,
            "page_query": params.urlencode(), "categories": categories, "selected": category,
            "collection_name": "All Products" if category == "all" else selected_category.name,
            "collection_description": selected_category.description if selected_category else "Discover the full ASTROL collection.",
            "collection_cover": cover, "q": q, "selected_origins": origins, "selected_mukhis": mukhis,
            "origins": origin_options, "mukhis": [str(n) for n in range(1, 22)], "price_filter": price, "sort": sort,
            "availability": availability, "has_filters": bool(active_filters), "active_filters": active_filters,
            "price_labels": price_labels}


def home(request):
    from .homepage import home_context
    return render(request, "store/home.html", home_context(request))


def catalog(request):
    return render(request, "store/catalog.html", _catalog_context(request))


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related("category").prefetch_related("variants"), slug=slug, active=True)
    variants = list(product.variants.all())
    selected_variant = min((v for v in variants if v.can_purchase), key=lambda v: v.price, default=None)
    related = Product.objects.filter(category=product.category, active=True).exclude(id=product.id).prefetch_related("variants")[:5]
    return render(request, "store/product_detail.html", {"product": product, "related": related,
                  "variants": variants, "selected_variant": selected_variant, "selected": product.category.slug})


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product.objects.prefetch_related("variants"), id=product_id, active=True)
    if not product.can_purchase:
        return HttpResponseBadRequest("This product is not available to purchase.")
    variants = list(product.variants.all())
    variant_id = request.POST.get("variant")
    variant = None
    if variant_id:
        variant = next((v for v in variants if str(v.pk) == variant_id), None)
        if variant is None:
            return HttpResponseBadRequest("Please choose a valid product option.")
    elif len(variants) == 1:
        variant = variants[0]
    elif len(variants) > 1:
        return redirect(product.get_absolute_url())
    if variant and not variant.can_purchase:
        return HttpResponseBadRequest("This option is not available to purchase.")
    cart = request.session.get("cart", {})
    key = f"{product.pk}:{variant.pk}" if variant else str(product.pk)
    next_quantity = cart.get(key, 0) + 1
    stock = variant.stock_quantity if variant else product.stock_quantity
    if stock is not None and next_quantity > stock:
        messages.error(request, "Your cart already contains the available quantity for this item.")
        return redirect(product.get_absolute_url())
    cart[key] = next_quantity
    request.session["cart"] = cart
    messages.success(request, f"{product.name} added to your cart.", extra_tags="cart")
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER", "")
    if not url_has_allowed_host_and_scheme(next_url, {request.get_host()}, require_https=request.is_secure()):
        next_url = "/cart/"
    return redirect(next_url)


def cart(request):
    raw = request.session.get("cart", {})
    items = []
    total = Decimal("0")
    cleaned = {}
    current = market(request)
    display_total = Decimal('0')
    for key, qty in raw.items():
        if not re.fullmatch(r"[0-9]+(?::[0-9]+)?", key) or not isinstance(qty, int) or qty < 1:
            continue
        pid, _, vid = key.partition(":")
        product = Product.objects.filter(id=int(pid), active=True).first()
        if not product or not product.can_purchase:
            continue
        variant = product.variants.filter(pk=int(vid), available=True, price__gt=0).first() if vid else None
        if vid and (not variant or not variant.can_purchase):
            continue
        if not vid and product.variants.exists():
            continue
        stock = variant.stock_quantity if variant else product.stock_quantity
        if stock is not None and qty > stock:
            qty = stock
            messages.warning(request, f"The quantity of {product.name} was adjusted to the available stock.")
        line = (variant.price if variant else product.price) * qty
        total += line
        display_line = convert(variant.price if variant else product.price, current) * qty
        display_total += display_line
        cleaned[key] = qty
        items.append({"product": product, "variant": variant, "key": key, "qty": qty, "line_total": line, "display_line": display_line})
    if cleaned != raw:
        request.session["cart"] = cleaned
    return render(request, "store/cart.html", {"items": items, "total": total, "display_total": display_total})


@require_POST
def remove_from_cart(request, product_key):
    cart = request.session.get("cart", {})
    cart.pop(product_key, None)
    request.session["cart"] = cart
    return redirect("cart")
