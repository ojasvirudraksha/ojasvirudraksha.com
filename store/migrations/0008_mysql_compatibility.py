from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("store", "0007_storecontact_secondary_phone_number")]

    operations = [
        migrations.AlterField(
            model_name="product", name="slug",
            field=models.SlugField(max_length=200, unique=True),
        ),
        migrations.RemoveConstraint(
            model_name="customeraddress", name="one_default_customer_address",
        ),
        migrations.AddConstraint(
            model_name="customeraddress",
            constraint=models.UniqueConstraint(
                models.Case(
                    models.When(is_default=True, then=models.F("user")),
                    default=None, output_field=models.BigIntegerField(),
                ),
                name="one_default_customer_address",
            ),
        ),
    ]
