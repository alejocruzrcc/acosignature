from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0002_documentsignatory'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='document',
            options={
                'ordering': ('-created_at',),
                'verbose_name': 'Documento',
                'verbose_name_plural': 'Documentos',
            },
        ),
        migrations.AlterModelOptions(
            name='documentsignatory',
            options={
                'ordering': ('id',),
                'verbose_name': 'Firmante del documento',
                'verbose_name_plural': 'Firmantes del documento',
            },
        ),
    ]
