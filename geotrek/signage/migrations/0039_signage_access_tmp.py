# Generated by Django 3.2.21 on 2023-12-01 15:50

from django.db import migrations, models
import django.db.models.deletion


def reset_accessmean_id(apps, schema_editor):
    Signage = apps.get_model('signage', 'Signage')
    Common_AccessMean = apps.get_model('common', 'AccessMean')

    for signage in Signage.objects.filter(access__isnull=False):
        access, create = Common_AccessMean.objects.get_or_create(label=signage.access.label)
        signage.access_tmp = access
        signage.save()


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0036_accessmean'),
        ('signage', '0038_auto_20231023_1233'),
    ]

    operations = [
        migrations.AddField(
            model_name='signage',
            name='access_tmp',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='common.accessmean', verbose_name='Access mean'),
        ),
        migrations.RunPython(reset_accessmean_id, reverse_code=migrations.RunPython.noop),
    ]
