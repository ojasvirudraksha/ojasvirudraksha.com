import os
import secrets
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = 'Create the first local ASTROL owner account and save its generated login privately.'

    def handle(self, *args, **options):
        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write('An owner account already exists. No login was changed.')
            return
        username = 'astrol_owner'
        if User.objects.filter(username=username).exists():
            raise CommandError('This username already exists. Use createsuperuser with another username.')
        directory = Path(settings.BASE_DIR) / '.local'
        directory.mkdir(mode=0o700, exist_ok=True)
        path = directory / 'admin-access.txt'
        password = secrets.token_urlsafe(24)
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as error:
            raise CommandError('A local credential file already exists; it has not been overwritten.') from error
        with os.fdopen(descriptor, 'w') as output:
            with transaction.atomic():
                User.objects.create_superuser(username=username, password=password)
                output.write(f'ASTROL local admin access\n\nPortal: http://127.0.0.1:8000/admin/\nUsername: {username}\nPassword: {password}\n\nChange your password after signing in using the Change password link.\nCustomer portal: http://127.0.0.1:8000/\n')
        self.stdout.write(self.style.SUCCESS(f'Owner account created. Login details saved privately to {path}'))
