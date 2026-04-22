from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentSignatory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('signed', 'Signed')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='signatories', to='documents.document')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='document_signatories', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('id',),
                'unique_together': {('document', 'user')},
            },
        ),
    ]
