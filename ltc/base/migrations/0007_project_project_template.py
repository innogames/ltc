# Generated by Django 2.2.20 on 2021-05-31 16:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('analyzer', '0008_reportcache'),
        ('base', '0006_auto_20210526_1446'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='project_template',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='related_project', to='analyzer.ReportTemplate'),
        ),
    ]
