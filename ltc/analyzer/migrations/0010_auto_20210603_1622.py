# Generated by Django 2.2.20 on 2021-06-03 14:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analyzer', '0009_graphitevariable_period'),
    ]

    operations = [
        migrations.AlterField(
            model_name='graphitevariable',
            name='period',
            field=models.CharField(blank=True, default='', max_length=12),
        ),
    ]
