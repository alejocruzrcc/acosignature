from django.db import migrations, models


def populate_sign_order(apps, schema_editor):
    DocumentSignatory = apps.get_model('documents', 'DocumentSignatory')
    document_ids = (
        DocumentSignatory.objects.order_by()
        .values_list('document_id', flat=True)
        .distinct()
    )
    for document_id in document_ids:
        signatories = DocumentSignatory.objects.filter(document_id=document_id).order_by('id')
        for index, signatory in enumerate(signatories, start=1):
            signatory.sign_order = index
            signatory.save(update_fields=['sign_order'])


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0005_documentsignatory_rejection_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='documentsignatory',
            name='sign_order',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.RunPython(populate_sign_order, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name='documentsignatory',
            options={
                'ordering': ('sign_order', 'id'),
                'verbose_name': 'Firmante del documento',
                'verbose_name_plural': 'Firmantes del documento',
            },
        ),
        migrations.AddConstraint(
            model_name='documentsignatory',
            constraint=models.UniqueConstraint(fields=('document', 'sign_order'), name='uniq_document_sign_order'),
        ),
    ]
