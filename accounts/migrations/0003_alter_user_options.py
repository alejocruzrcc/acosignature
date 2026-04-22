from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_alter_user_options_alter_user_date_joined_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={
                'verbose_name': 'Usuario',
                'verbose_name_plural': 'Usuarios',
            },
        ),
    ]
