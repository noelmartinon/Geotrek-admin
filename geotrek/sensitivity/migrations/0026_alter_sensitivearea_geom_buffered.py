# Generated by Django 3.2.15 on 2022-11-18 08:56

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sensitivity', '0025_auto_20221117_1734'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sensitivearea',
            name='geom_buffered',
            field=django.contrib.gis.db.models.fields.GeometryField(default=None, editable=False, srid=2154),
            preserve_default=False,
        ),
    ]
