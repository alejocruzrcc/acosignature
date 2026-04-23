from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0003_alter_document_options_alter_documentsignatory_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='signed_file',
            field=models.FileField(blank=True, null=True, upload_to='documents/signed/'),
        ),
    ]
