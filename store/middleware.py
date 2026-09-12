from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect


class UserPortalSeparationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            is_admin_path = request.path.startswith('/admin/')
            is_customer_path = (
                request.path == '/'
                or request.path.startswith('/account/')
                or request.path.startswith('/cart/')
                or request.path.startswith('/shop/')
                or request.path.startswith('/product/')
                or request.path.startswith('/contact/')
                or request.path.startswith('/help/')
                or request.path.startswith('/newsletter/')
            )

            if request.user.is_staff or request.user.is_superuser:
                if not is_admin_path and not request.path.startswith('/admin/login/'):
                    logout(request)
                    messages.error(request, 'Staff accounts must use the admin portal.')
                    return redirect(f'/admin/login/?next={quote(request.get_full_path())}')
            elif is_admin_path and not request.path.startswith('/admin/login/'):
                logout(request)
                messages.error(request, 'Customer accounts cannot access the admin portal.')
                return redirect(f'/account/login/?next={quote(request.get_full_path())}')

        return self.get_response(request)
