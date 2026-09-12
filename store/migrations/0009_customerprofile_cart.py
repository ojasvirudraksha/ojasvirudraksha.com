from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("store", "0008_mysql_compatibility")]
    operations = [
        migrations.AddField(
            model_name="customerprofile", name="cart",
            field=models.JSONField(default=dict, blank=True, editable=False),
        ),
    ]
