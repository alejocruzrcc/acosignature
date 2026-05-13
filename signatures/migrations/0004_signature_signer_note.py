from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('signatures', '0003_alter_signature_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='signature',
            name='signer_note',
            field=models.TextField(blank=True, default=''),
        ),
    ]
