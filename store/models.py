from django.db import models
from django.urls import reverse
from django.templatetags.static import static
from django.db.models import Q
from django.core.validators import MinValueValidator


class ProductQuerySet(models.QuerySet):
    def purchasable(self):
        variant_stock = Q(variants__stock_quantity__isnull=True) | Q(variants__stock_quantity__gt=0)
        product_stock = Q(stock_quantity__isnull=True) | Q(stock_quantity__gt=0)
        return self.filter(active=True, available=True, is_sample=False).filter(
            (Q(variants__isnull=True, price__gt=0) & product_stock)
            | (Q(variants__available=True, variants__price__gt=0) & variant_stock)
        ).distinct()



class Category(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    objects = ProductQuerySet.as_manager()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    collections = models.ManyToManyField(Category, blank=True, related_name="collection_products")
    name = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)
    origin = models.CharField(max_length=80, blank=True)
    size = models.CharField(max_length=60, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image = models.CharField(max_length=255, blank=True, help_text="Existing static image path. An uploaded photo takes precedence.")
    uploaded_image = models.ImageField(upload_to="products/%Y/%m/", blank=True)
    sku = models.CharField(max_length=100, blank=True)
    stock_quantity = models.PositiveIntegerField(null=True, blank=True, help_text="Leave blank if stock is not tracked. Zero means sold out. For products with options, edit stock on each variant.")
    short_description = models.CharField(max_length=240, blank=True)
    description = models.TextField(blank=True)
    featured = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    available = models.BooleanField(default=True)
    is_sample = models.BooleanField(default=False)
    source_id = models.CharField(max_length=40, unique=True, null=True, blank=True)
    source_url = models.URLField(blank=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("product_detail", args=[self.slug])

    @property
    def has_options(self):
        return len(self.variants.all()) > 1

    @property
    def can_purchase(self):
        if not self.active or not self.available or self.is_sample:
            return False
        variants = list(self.variants.all())
        if variants:
            return any(v.can_purchase for v in variants)
        return self.price > 0 and (self.stock_quantity is None or self.stock_quantity > 0)

    @property
    def image_url(self):
        return self.uploaded_image.url if self.uploaded_image else static(self.image or "images/exact/logo.png")

    def refresh_variant_price(self):
        variants = list(self.variants.all())
        if variants:
            cheapest = min([v for v in variants if v.can_purchase] or variants, key=lambda v: v.price)
            type(self).objects.filter(pk=self.pk).update(price=cheapest.price, compare_at_price=cheapest.compare_at_price)
            self.price = cheapest.price
            self.compare_at_price = cheapest.compare_at_price


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    source_id = models.CharField(max_length=40, unique=True, null=True, blank=True)
    name = models.CharField(max_length=180)
    sku = models.CharField(max_length=100, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    available = models.BooleanField(default=True)
    position = models.PositiveIntegerField(default=0)
    stock_quantity = models.PositiveIntegerField(null=True, blank=True, help_text="Blank = not tracked; 0 = sold out.")

    @property
    def can_purchase(self):
        return self.available and self.price > 0 and (self.stock_quantity is None or self.stock_quantity > 0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return f"{self.product.name} — {self.name}"


class CustomerProfile(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='customer_profile')
    phone = models.CharField(max_length=25, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.email or self.user.username


class CustomerAddress(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='addresses')
    label = models.CharField(max_length=40, default='Home')
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=25)
    address_line1 = models.CharField('Address line 1', max_length=200)
    address_line2 = models.CharField('Address line 2', max_length=200, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField('State / region', max_length=100)
    postal_code = models.CharField('Postal / ZIP code', max_length=20)
    country = models.CharField(max_length=100, default='India')
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_default', 'id']
        constraints = [models.UniqueConstraint(fields=['user'], condition=Q(is_default=True), name='one_default_customer_address')]
        verbose_name_plural = 'Customer addresses'

    def __str__(self):
        return f'{self.full_name} — {self.label}, {self.city}'


class WishlistItem(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [models.UniqueConstraint(fields=['user', 'product'], name='unique_customer_wishlist_product')]

    def __str__(self):
        return f'{self.user.username} — {self.product.name}'


class InformationPage(models.Model):
    title = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    intro = models.TextField(blank=True)
    body = models.TextField(help_text='Plain text. Separate paragraphs with a blank line.')
    needs_confirmation = models.BooleanField(default=False, help_text='Show that business policy details are still being finalized.')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class StoreContact(models.Model):
    support_email = models.EmailField(blank=True)
    whatsapp_number = models.CharField(max_length=20, blank=True, help_text='International number, including country code; digits only.')
    secondary_phone_number = models.CharField(max_length=20, blank=True, help_text='Additional contact number, including country code; digits only.')
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)

    def __str__(self):
        return 'ASTROL contact and social links'


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.email


class SupportEnquiry(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=160)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Support enquiries'

    def __str__(self):
        return self.subject
