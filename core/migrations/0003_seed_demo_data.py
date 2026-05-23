from django.db import migrations


def skip_demo_data(apps, schema_editor):
    # Demo data seeding is intentionally disabled for production deployments.
    return None


class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('accounts', '0002_alter_expense_options_alter_expensecategory_options_and_more'),
        ('inventory', '0001_initial'),
        ('sales', '0002_offlinesalequeue'),
        ('core', '0002_alter_shopsettings_shop_name'),
    ]

    operations = [
        migrations.RunPython(skip_demo_data, migrations.RunPython.noop),
    ]
