# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orb', '0003_auto_20150420_2152'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resourceworkflowtracker',
            name='status',
            field=models.CharField(default=b'pending_crt', max_length=50, choices=[(b'rejected', 'Rejected'), (b'pending_crt', 'Pending CRT'), (b'pending_mep', 'Pending MEP'), (b'approved', 'Approved')]),
            preserve_default=True,
        ),
    ]
