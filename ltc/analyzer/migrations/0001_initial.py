# Generated by Django 2.2.20 on 2021-05-05 15:51

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('base', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Action',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField()),
                ('description', models.TextField(blank=True, null=True)),
                ('project', models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='base.Project')),
            ],
            options={
                'unique_together': {('name', 'project')},
            },
        ),
        migrations.CreateModel(
            name='Error',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField(db_index=True)),
                ('code', models.CharField(blank=True, max_length=400, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Server',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('server_name', models.TextField()),
                ('description', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='TestDataResolution',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('frequency', models.CharField(max_length=100)),
                ('per_sec_divider', models.IntegerField(default=60)),
            ],
        ),
        migrations.CreateModel(
            name='TestError',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('count', models.IntegerField(default=0)),
                ('action', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analyzer.Action')),
                ('error', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analyzer.Error')),
                ('test', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.Test')),
            ],
        ),
        migrations.CreateModel(
            name='TestData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(default='default', max_length=100)),
                ('data', django.contrib.postgres.fields.jsonb.JSONField()),
                ('data_resolution', models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='analyzer.TestDataResolution')),
                ('test', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.Test')),
            ],
        ),
        migrations.CreateModel(
            name='TestActionData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', django.contrib.postgres.fields.jsonb.JSONField()),
                ('action', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='analyzer.Action')),
                ('data_resolution', models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='analyzer.TestDataResolution')),
                ('test', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.Test')),
            ],
            options={
                'index_together': {('test', 'action', 'data_resolution')},
            },
        ),
        migrations.CreateModel(
            name='TestActionAggregateData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', django.contrib.postgres.fields.jsonb.JSONField()),
                ('action', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analyzer.Action')),
                ('test', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.Test')),
            ],
            options={
                'index_together': {('test', 'action')},
            },
        ),
        migrations.CreateModel(
            name='ServerMonitoringData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.TextField(default='default')),
                ('data', django.contrib.postgres.fields.jsonb.JSONField()),
                ('data_resolution', models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='analyzer.TestDataResolution')),
                ('server', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analyzer.Server')),
                ('test', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.Test')),
            ],
            options={
                'index_together': {('test', 'server', 'source', 'data_resolution')},
            },
        ),
    ]
