from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0004_document_signed_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='documentsignatory',
            name='rejected_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='documentsignatory',
            name='rejection_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='documentsignatory',
            name='status',
            field=models.CharField(
                choices=[('pending', 'Pending'), ('signed', 'Signed'), ('rejected', 'Rejected')],
                default='pending',
                max_length=20,
            ),
        ),
    ]
