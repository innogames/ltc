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

    class Meta:
        db_table = 'project'

    def __str__(self):
        return self.project_name


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

    class Meta:
        db_table = 'test'

    def __str__(self):
        return self.display_name


class TestData(models.Model):
    test = models.ForeignKey(Test)
    data = JSONField()

    class Meta:
        db_table = 'test_data'


class Action(models.Model):
    url = models.CharField(max_length=100)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, default=1)
    description = models.CharField(max_length=400, null=True, blank=True)

    class Meta:
        db_table = 'action'
        unique_together = (('url', 'project'))


class TestActionData(models.Model):
    test = models.ForeignKey(Test)
    action = models.ForeignKey(Action, null=True, blank=True)
    data = JSONField()

    class Meta:
        db_table = 'test_action_data'
        index_together = [
            ("test", "action"),
        ]


class Aggregate(models.Model):
    test = models.ForeignKey(Test)
    action = models.ForeignKey(Action, null=True, blank=True)
    average = models.FloatField()
    median = models.FloatField()
    percentile_75 = models.FloatField()
    percentile_90 = models.FloatField()
    percentile_99 = models.FloatField()
    maximum = models.FloatField()
    minimum = models.FloatField()
    count = models.IntegerField(default=0)
    errors = models.IntegerField(default=0, null=True, blank=True)
    weight = models.FloatField()

    class Meta:
        db_table = 'aggregate'
        unique_together = (('test', 'action'))


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
            ("test", "action"),
        ]


class Server(models.Model):
    server_name = models.CharField(max_length=100)
    description = models.CharField(max_length=400, null=True, blank=True)

    class Meta:
        db_table = 'server'


class ServerMonitoringData(models.Model):
    test = models.ForeignKey(Test)
    server = models.ForeignKey(Server)
    data = JSONField()

    class Meta:
        db_table = 'server_monitoring_data'


admin.site.register(Project)
