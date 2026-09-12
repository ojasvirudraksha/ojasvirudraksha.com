from django.urls import path, include
from . import views, help_views
urlpatterns=[
    path('pages/<slug:slug>/', help_views.page, name='information_page'),
    path('contact/', help_views.contact, name='contact_us'),
    path('newsletter/', help_views.newsletter, name='newsletter'),
    path('newsletter/subscribe/', help_views.subscribe, name='newsletter_subscribe'),
    path("country/", views.set_country, name="set_country"),
    path("account/", include("store.account_urls")),
    path("",views.home,name="home"),
    path("shop/",views.catalog,name="catalog"),
    path("product/<slug:slug>/",views.product_detail,name="product_detail"),
    path("cart/",views.cart,name="cart"),
    path("cart/add/<int:product_id>/",views.add_to_cart,name="add_to_cart"),
    path("cart/remove/<str:product_key>/",views.remove_from_cart,name="remove_from_cart"),
]
