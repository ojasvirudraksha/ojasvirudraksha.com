from django.contrib import admin
from django.urls import path, include
from django.urls import reverse_lazy
from django.contrib.auth import views as auth
from store.account_forms import AdminPasswordResetForm
from store.admin_profile import profile as admin_profile
urlpatterns = [
    path('admin/profile/', admin.site.admin_view(admin_profile), name='admin_profile'),
    path('admin/password-reset/', auth.PasswordResetView.as_view(
        form_class=AdminPasswordResetForm, template_name='admin/password_reset.html',
        email_template_name='admin/reset_email.txt', subject_template_name='accounts/reset_subject.txt',
        success_url=reverse_lazy('admin_password_reset_done')), name='admin_password_reset'),
    path('admin/password-reset/sent/', auth.PasswordResetDoneView.as_view(
        template_name='admin/password_reset.html', extra_context={'reset_sent': True}), name='admin_password_reset_done'),
    path('admin/password-reset/complete/', auth.PasswordResetCompleteView.as_view(
        template_name='admin/password_reset.html', extra_context={'reset_complete': True}), name='admin_password_reset_complete'),
    path('admin/password-reset/<uidb64>/<token>/', auth.PasswordResetConfirmView.as_view(
        template_name='admin/password_reset.html', extra_context={'reset_confirm': True},
        success_url=reverse_lazy('admin_password_reset_complete')), name='admin_password_reset_confirm'),
    path("admin/", admin.site.urls),
    path("", include("store.urls")),
]

from django.conf import settings
from django.conf.urls.static import static
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
