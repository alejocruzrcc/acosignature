from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('signatures', '0002_alter_signature_unique_together'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='signature',
            options={
                'ordering': ('-signed_at',),
                'verbose_name': 'Firma',
                'verbose_name_plural': 'Firmas',
            },
        ),
    ]
