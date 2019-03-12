from __future__ import unicode_literals

from django.db import models
from django.contrib.postgres.fields import JSONField
from django.contrib import admin
# Create your models here.
from administrator.models import JMeterProfile, User


class Project(models.Model):
    project_name = models.CharField(max_length=100)
    jmeter_parameters = JSONField(null=True, blank=True)
    script_parameters = JSONField(null=True, blank=True)
    jmeter_profile = models.ForeignKey(
        JMeterProfile, null=True, blank=True, on_delete=models.CASCADE)
    test_plan_destination = models.CharField(
        max_length=200, null=True, blank=True)
    jvm_args = models.TextField(null=True, blank=True)
    jmeter_remote_instances = JSONField(null=True, blank=True)
    script_pre = models.TextField(null=True, blank=True)
    script_post = models.TextField(null=True, blank=True)
    show = models.BooleanField(default=True)
    confluence_space = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'project'

    def __str__(self):
        return self.project_name



class TestDataResolution(models.Model):
    frequency = models.CharField(max_length=100)
    per_sec_divider = models.IntegerField(default=60)

    class Meta:
        db_table = 'test_data_resolution'


class Test(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    path = models.CharField(max_length=200)
    display_name = models.CharField(max_length=100)
    description = models.CharField(max_length=4000, null=True, blank=True)
    parameters = JSONField(null=True, blank=True)
    start_time = models.BigIntegerField(db_index=True)
    end_time = models.BigIntegerField(default=0)
    build_number = models.IntegerField(default=0)
    show = models.BooleanField(default=True)
    started_by = models.ForeignKey(User, on_delete=models.CASCADE, default=0)
    data_resolution = models.CharField(max_length=100, default='1Min')

    class Meta:
        db_table = 'test'
        index_together = [
            ('show', 'project', 'start_time'),
        ]

    def __str__(self):
        return self.display_name


class TestData(models.Model):
    test = models.ForeignKey(Test)
    data_resolution = models.ForeignKey(TestDataResolution, default=1)
    source = models.CharField(max_length=100, default='default')
    data = JSONField()

    class Meta:
        db_table = 'test_data'


class Action(models.Model):
    url = models.TextField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE, default=1)
    description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'action'
        unique_together = (('url', 'project'))


class Error(models.Model):
    text = models.TextField(db_index=True)
    code = models.CharField(max_length=400, null=True, blank=True)

    class Meta:
        db_table = 'error'


class TestError(models.Model):
    test = models.ForeignKey(Test)
    action = models.ForeignKey(Action)
    error = models.ForeignKey(Error)
    count = models.IntegerField(default=0)

    class Meta:
        db_table = 'test_error'


class TestActionData(models.Model):
    test = models.ForeignKey(Test)
    data_resolution = models.ForeignKey(TestDataResolution, default=1)
    action = models.ForeignKey(Action, null=True, blank=True)
    data = JSONField()

    class Meta:
        db_table = 'test_action_data'
        index_together = [
            ('test', 'action','data_resolution'),
        ]


class TestAggregate(models.Model):
    test = models.ForeignKey(Test)
    data = JSONField()

    class Meta:
        db_table = 'test_aggregate'


class TestActionAggregateData(models.Model):
    test = models.ForeignKey(Test)
    action = models.ForeignKey(Action)
    data = JSONField()

    class Meta:
        db_table = 'test_action_aggregate_data'
        index_together = [
            ('test', 'action'),
        ]


class Server(models.Model):
    server_name = models.CharField(max_length=100)
    description = models.CharField(max_length=400, null=True, blank=True)

    class Meta:
        db_table = 'server'


class ServerMonitoringData(models.Model):
    test = models.ForeignKey(Test)
    data_resolution = models.ForeignKey(TestDataResolution, default=1)
    source = models.CharField(max_length=100, default='default')
    server = models.ForeignKey(Server)
    data = JSONField()

    class Meta:
        db_table = 'server_monitoring_data'
        index_together = [
            ('test', 'server', 'source','data_resolution'),
        ]


class TestResultFile(models.Model):
    #project = models.ForeignKey(Project, on_delete=models.CASCADE, default=1)
    #test = models.ForeignKey(Test)
    file = models.FileField(upload_to='test_result_files/')

    #uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'test_result_file'
