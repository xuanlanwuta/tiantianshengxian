# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='goodssku',
            name='category',
            field=models.ForeignKey(on_delete=False, to='goods.GoodsCategory', verbose_name='类别'),
        ),
    ]
