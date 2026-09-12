import re

from django.db import migrations


def rename_brand(value):
    def replacement(match):
        text = match.group()
        if text.isupper():
            return 'OJASVIRUDRAKSHA'
        if text.islower():
            return 'ojasvirudraksha'
        return 'Ojasvirudraksha'
    return re.sub(r'(?<![a-z])astrol(?![a-z])', replacement, value, flags=re.IGNORECASE)


def update_brand(apps, schema_editor):
    # Change brand copy in place so product IDs, carts and wishlists stay intact.
    alias = schema_editor.connection.alias
    for model_name, fields in (
        ('Product', ('name', 'slug', 'short_description', 'description', 'image')),
        ('Category', ('name', 'description')),
        ('InformationPage', ('title', 'intro', 'body')),
    ):
        Model = apps.get_model('store', model_name)
        for row in Model.objects.using(alias).all().iterator():
            updates = {}
            for field in fields:
                old = getattr(row, field)
                new = rename_brand(old)
                if field == 'image' and old == 'images/exact/logo.png':
                    new = 'images/ojasvirudraksha-logo.svg'
                if new != old:
                    updates[field] = new
            if updates:
                Model.objects.using(alias).filter(pk=row.pk).update(**updates)


class Migration(migrations.Migration):
    dependencies = [('store', '0009_customerprofile_cart')]
    operations = [migrations.RunPython(update_brand, migrations.RunPython.noop)]
