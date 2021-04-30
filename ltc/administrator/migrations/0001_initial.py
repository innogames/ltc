# Generated by Django 2.2.20 on 2021-04-30 13:20

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Configuration',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=1000)),
                ('value', models.CharField(default='', max_length=1000)),
                ('description', models.CharField(default='', max_length=1000)),
                ('secure', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'configuration',
            },
        ),
        migrations.CreateModel(
            name='JMeterProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=1000)),
                ('path', models.CharField(default='', max_length=1000)),
                ('version', models.CharField(default='', max_length=1000)),
                ('jvm_args_main', models.CharField(default='-Xms2g -Xmx2g', max_length=1000)),
                ('jvm_args_jris', models.CharField(default='-Xms2g -Xmx2g', max_length=1000)),
            ],
            options={
                'db_table': 'jmeter_profile',
            },
        ),
        migrations.CreateModel(
            name='SSHKey',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('path', models.CharField(default='', max_length=1000)),
                ('description', models.CharField(default='', max_length=1000)),
                ('default', models.BooleanField(default=True)),
            ],
            options={
                'db_table': 'ssh_key',
            },
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('login', models.CharField(max_length=100)),
            ],
            options={
                'db_table': 'user',
            },
        ),
    ]
