from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('workflows', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='auditevent',
            options={
                'ordering': ('-created_at',),
                'verbose_name': 'Evento de auditoría',
                'verbose_name_plural': 'Eventos de auditoría',
            },
        ),
    ]
