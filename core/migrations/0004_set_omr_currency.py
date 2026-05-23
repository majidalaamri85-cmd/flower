from django.db import migrations, models


def set_omr_currency(apps, schema_editor):
    ShopSettings = apps.get_model('core', 'ShopSettings')
    ShopSettings.objects.filter(currency_symbol__in=['ريال', 'SAR', 'ر.س']).update(currency_symbol='ر.ع')


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0003_seed_demo_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='shopsettings',
            name='currency_symbol',
            field=models.CharField(default='ر.ع', max_length=10),
        ),
        migrations.RunPython(set_omr_currency, migrations.RunPython.noop),
    ]
