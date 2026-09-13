from django.db import migrations


def populate_contact_numbers(apps, schema_editor):
    Contact = apps.get_model('store', 'StoreContact')
    contacts = Contact.objects.using(schema_editor.connection.alias)
    contact = contacts.order_by('pk').first()
    if contact is None:
        contact = contacts.create()
    changed = []
    for field, number in (('whatsapp_number', '917065356503'),
                          ('secondary_phone_number', '917906648194')):
        if not getattr(contact, field).strip():
            setattr(contact, field, number)
            changed.append(field)
    if changed:
        contact.save(using=schema_editor.connection.alias, update_fields=changed)


class Migration(migrations.Migration):
    dependencies = [('store', '0011_staffprofile')]
    operations = [migrations.RunPython(populate_contact_numbers, migrations.RunPython.noop)]
