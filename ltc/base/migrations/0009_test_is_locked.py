# Generated by Django 2.2 on 2022-03-16 12:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0008_configuration'),
    ]

    operations = [
        migrations.AddField(
            model_name='test',
            name='is_locked',
            field=models.BooleanField(default=False),
        ),
    ]
