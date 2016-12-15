# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-12-15 13:28
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0013_auto_20161205_1519'),
    ]

    operations = [
        migrations.CreateModel(
            name='HighRiskLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('msg', models.CharField(max_length=2000)),
                ('context', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.ContextForWeek')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]