# Generated by Django 2.2.20 on 2021-05-26 15:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('analyzer', '0003_reporttemplate_body'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reportvariable',
            name='template',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='variables', to='analyzer.ReportTemplate'),
        ),
    ]
