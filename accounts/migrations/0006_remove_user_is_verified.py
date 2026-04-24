from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_user_signature_image'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='is_verified',
        ),
    ]
