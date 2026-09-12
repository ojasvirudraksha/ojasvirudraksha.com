from django.contrib import admin
from django.db.models import Q
from django.utils.html import format_html
from .models import Category, Product, ProductVariant

admin.site.site_header = 'ASTROL · Admin Portal'
admin.site.site_title = 'ASTROL Administration'
admin.site.index_title = 'Inventory overview'
admin.site.index_template = 'admin/inventory_index.html'
admin.site.site_url = '/'


class StockFilter(admin.SimpleListFilter):
    title = 'inventory status'
    parameter_name = 'stock_status'

    def lookups(self, request, model_admin):
        return [('low', 'Low stock (1–5)'), ('zero', 'Out of stock'), ('untracked', 'Not tracked'), ('positive', 'Stock available')]

    def queryset(self, request, queryset):
        if self.value() == 'low':
            return queryset.filter(stock_quantity__gte=1, stock_quantity__lte=5)
        if self.value() == 'zero':
            return queryset.filter(stock_quantity=0)
        if self.value() == 'untracked':
            return queryset.filter(stock_quantity__isnull=True)
        if self.value() == 'positive':
            return queryset.filter(stock_quantity__gt=0)
        return queryset


class ProductStockFilter(StockFilter):
    def queryset(self, request, queryset):
        value = self.value()
        if value == 'low':
            return queryset.filter(Q(variants__isnull=True, stock_quantity__gte=1, stock_quantity__lte=5) | Q(variants__stock_quantity__gte=1, variants__stock_quantity__lte=5)).distinct()
        if value == 'zero':
            return queryset.filter(Q(variants__isnull=True, stock_quantity=0) | Q(variants__stock_quantity=0)).distinct()
        if value == 'untracked':
            return queryset.filter(Q(variants__isnull=True, stock_quantity__isnull=True) | Q(variants__isnull=False, variants__stock_quantity__isnull=True)).distinct()
        if value == 'positive':
            return queryset.filter(Q(variants__isnull=True, stock_quantity__gt=0) | Q(variants__stock_quantity__gt=0)).distinct()
        return queryset


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


class VariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ('name', 'sku', 'price', 'compare_at_price', 'stock_quantity', 'available', 'position')
    show_change_link = True
    verbose_name_plural = 'Product options & stock — leave quantity blank if not tracked'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('photo', 'name', 'category', 'sku', 'price', 'stock_summary', 'available', 'active', 'is_sample')
    list_display_links = ('photo', 'name')
    list_filter = (ProductStockFilter, 'category', 'available', 'active', 'is_sample', 'featured')
    search_fields = ('name', 'sku', 'variants__sku', 'origin', 'source_id')
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('collections',)
    list_select_related = ('category',)
    list_per_page = 30
    readonly_fields = ('photo', 'stock_summary', 'source_id', 'source_url')
    inlines = [VariantInline]
    actions = ['publish_products', 'hide_products', 'enable_sales', 'pause_sales']
    fieldsets = (
        ('Product details', {'fields': ('name', 'slug', 'category', 'collections', 'sku', 'origin', 'size')}),
        ('Photos', {'fields': ('photo', 'uploaded_image', 'image')}),
        ('Price & inventory', {'fields': ('price', 'compare_at_price', 'stock_quantity', 'stock_summary', 'available'),
                               'description': 'Products with options use the prices and quantities in the variant rows below. Blank quantities mean not tracked. Adding an item to a cart does not reserve or deduct stock.'}),
        ('Storefront', {'fields': ('active', 'featured', 'is_sample', 'short_description', 'description')}),
        ('Reference information', {'fields': ('source_id', 'source_url'), 'classes': ('collapse',)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('variants')

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.variants.exists():
            fields += ['price', 'compare_at_price', 'stock_quantity']
        return fields

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.refresh_from_db()
        form.instance.refresh_variant_price()

    @admin.display(description='Photo')
    def photo(self, obj):
        if obj and obj.pk:
            return format_html('<img src="{}" alt="" width="52" height="52" style="object-fit:contain;border-radius:5px;background:white">', obj.image_url)
        return 'Upload a photo after entering the product details.'

    @admin.display(description='Inventory')
    def stock_summary(self, obj):
        variants = list(obj.variants.all()) if obj.pk else []
        if variants:
            untracked = sum(v.stock_quantity is None for v in variants)
            units = sum(v.stock_quantity or 0 for v in variants)
            return f'{units} tracked units · {untracked} options not tracked' if untracked else f'{units} units across {len(variants)} options'
        return 'Not tracked' if obj.stock_quantity is None else f'{obj.stock_quantity} units'

    @admin.action(description='Publish selected products', permissions=['change'])
    def publish_products(self, request, queryset):
        self.message_user(request, f'{queryset.update(active=True)} products published.')

    @admin.action(description='Hide selected products from storefront', permissions=['change'])
    def hide_products(self, request, queryset):
        self.message_user(request, f'{queryset.update(active=False)} products hidden.')

    @admin.action(description='Enable sales (stock and sample restrictions still apply)', permissions=['change'])
    def enable_sales(self, request, queryset):
        self.message_user(request, f'{queryset.update(available=True)} products enabled.')

    @admin.action(description='Pause sales for selected products', permissions=['change'])
    def pause_sales(self, request, queryset):
        self.message_user(request, f'{queryset.update(available=False)} products paused.')


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'sku', 'price', 'stock_quantity', 'available')
    list_display_links = ('name',)
    list_editable = ('price', 'stock_quantity', 'available')
    list_filter = (StockFilter, 'available', 'product__category')
    search_fields = ('product__name', 'name', 'sku', 'source_id')
    list_select_related = ('product',)
    autocomplete_fields = ('product',)
    readonly_fields = ('source_id',)
    fields = ('product', 'name', 'sku', 'price', 'compare_at_price', 'stock_quantity', 'available', 'position', 'source_id')
    list_per_page = 30

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + (('product',) if obj else ())


from .models import CustomerProfile, CustomerAddress, WishlistItem


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'email', 'phone', 'created_at')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'phone')
    list_select_related = ('user',)
    readonly_fields = ('created_at', 'updated_at', 'email')
    autocomplete_fields = ('user',)
    fields = ('user', 'email', 'phone', 'created_at', 'updated_at')

    @admin.display(description='Customer')
    def customer_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description='Email')
    def email(self, obj):
        return obj.user.email

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + (('user',) if obj else ())


@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'label', 'city', 'country', 'is_default')
    list_filter = ('country', 'is_default')
    search_fields = ('full_name', 'user__email', 'phone', 'city', 'postal_code')
    autocomplete_fields = ('user',)
    list_select_related = ('user',)


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    list_select_related = ('user', 'product')
    search_fields = ('user__email', 'product__name')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('user', 'product')


from .models import InformationPage, StoreContact, NewsletterSubscriber, SupportEnquiry

@admin.register(InformationPage)
class InformationPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'needs_confirmation', 'updated_at')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'body')

@admin.register(StoreContact)
class StoreContactAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return super().has_add_permission(request) and not StoreContact.objects.exists()

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'active', 'subscribed_at')
    search_fields = ('email',)
    list_filter = ('active',)
    readonly_fields = ('subscribed_at',)

@admin.register(SupportEnquiry)
class SupportEnquiryAdmin(admin.ModelAdmin):
    list_display = ('subject', 'name', 'email', 'resolved', 'created_at')
    list_filter = ('resolved',)
    search_fields = ('name', 'email', 'subject')
    readonly_fields = ('created_at',)
