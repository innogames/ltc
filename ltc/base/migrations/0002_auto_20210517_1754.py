# Generated by Django 2.2.20 on 2021-05-17 15:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='test',
            name='jmeter_heap',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='test',
            name='jmeter_path',
            field=models.TextField(blank=True, null=True),
        ),
    ]
