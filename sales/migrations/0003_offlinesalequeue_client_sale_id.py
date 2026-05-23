from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0002_offlinesalequeue'),
    ]

    operations = [
        migrations.AddField(
            model_name='offlinesalequeue',
            name='client_sale_id',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
    ]
