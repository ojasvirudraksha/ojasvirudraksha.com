from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect


class UserPortalSeparationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            is_admin_path = request.path.startswith('/admin/')
            if request.user.is_staff or request.user.is_superuser:
                # Staff may browse public storefront pages while managing inventory in
                # another tab. Customer account pages remain separate from the admin
                # account, but the staff session is retained for a smooth return.
                if request.path.startswith('/account/'):
                    messages.info(request, 'Customer account pages are unavailable to staff accounts.')
                    return redirect('/admin/')
            elif is_admin_path and not request.path.startswith('/admin/login/'):
                logout(request)
                messages.error(request, 'Customer accounts cannot access the admin portal.')
                return redirect(f'/account/login/?next={quote(request.get_full_path())}')

        return self.get_response(request)
