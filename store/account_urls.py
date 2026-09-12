from django.contrib.auth import views as auth
from django.urls import path, reverse_lazy
from . import account_views as views

urlpatterns = [
    path('', views.dashboard, name='account_dashboard'),
    path('login/', views.CustomerLoginView.as_view(), name='account_login'),
    path('register/', views.signup, name='account_signup'),
    path('logout/', auth.LogoutView.as_view(next_page='account_login'), name='account_logout'),
    path('profile/', views.profile, name='account_profile'),
    path('addresses/', views.addresses, name='account_addresses'),
    path('addresses/add/', views.address_edit, name='account_address_add'),
    path('addresses/<int:pk>/edit/', views.address_edit, name='account_address_edit'),
    path('addresses/<int:pk>/delete/', views.address_delete, name='account_address_delete'),
    path('wishlist/', views.wishlist, name='account_wishlist'),
    path('wishlist/update/', views.wishlist_update, name='account_wishlist_update'),
    path('orders/', views.orders, name='account_orders'),
    path('password/', auth.PasswordChangeView.as_view(template_name='accounts/password_change.html', success_url=reverse_lazy('account_password_done'), extra_context={'account_tab': 'security'}), name='account_password'),
    path('password/changed/', auth.PasswordChangeDoneView.as_view(template_name='accounts/password_changed.html', extra_context={'account_tab': 'security'}), name='account_password_done'),
    path('password/reset/', auth.PasswordResetView.as_view(template_name='accounts/password_reset.html', email_template_name='accounts/reset_email.txt', subject_template_name='accounts/reset_subject.txt', success_url=reverse_lazy('account_reset_done')), name='account_reset'),
    path('password/reset/sent/', auth.PasswordResetDoneView.as_view(template_name='accounts/password_reset_sent.html'), name='account_reset_done'),
    path('password/reset/<uidb64>/<token>/', auth.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html', success_url=reverse_lazy('account_reset_complete')), name='password_reset_confirm'),
    path('password/reset/complete/', auth.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'), name='account_reset_complete'),
]
