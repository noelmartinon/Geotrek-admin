# Generated by Django 3.1.13 on 2021-10-25 14:30

import django.contrib.postgres.functions
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0029_auto_20211022_1252'),
    ]

    operations = [
        migrations.AlterField(
            model_name='path',
            name='uuid',
            field=models.UUIDField(default=django.contrib.postgres.functions.RandomUUID(), editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='topology',
            name='uuid',
            field=models.UUIDField(default=django.contrib.postgres.functions.RandomUUID(), editable=False, unique=True),
        ),
    ]
