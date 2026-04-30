from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0007_document_archived'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='category',
            field=models.CharField(
                choices=[
                    ('COMPARATIVOS', 'COMPARATIVOS'),
                    ('SERVICIOS OBRA', 'SERVICIOS OBRA'),
                    ('DISEÑO', 'DISEÑO'),
                    ('MERCADERO', 'MERCADERO'),
                ],
                default='COMPARATIVOS',
                max_length=30,
            ),
        ),
    ]
