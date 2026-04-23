from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0004_user_cargo'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='signature_image',
            field=models.ImageField(blank=True, null=True, upload_to='user_signatures/'),
        ),
    ]
