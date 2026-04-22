from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('signatures', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='signature',
            unique_together=set(),
        ),
    ]
