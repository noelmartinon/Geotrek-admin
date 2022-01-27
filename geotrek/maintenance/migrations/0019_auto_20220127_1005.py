# Generated by Django 3.1.14 on 2022-01-27 09:05

import django.contrib.postgres.indexes
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0018_interventionjob_active'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='intervention',
            index=django.contrib.postgres.indexes.GistIndex(fields=['geom_3d'], name='intervention_geom_3d_gist_idx'),
        ),
    ]
