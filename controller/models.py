from __future__ import unicode_literals
from analyzer.models import Project
from django.contrib.postgres.fields import JSONField
from django.db import models

# Create your models here.
from administrator.models import SSHKey
from online.models import RunningTest

class Proxy(models.Model):
    port = models.IntegerField(default=0)
    pid = models.IntegerField(default=0)
    destination = models.CharField(max_length=200, default="https://dest")
    destination_port = models.IntegerField(default=443)
    delay = models.FloatField()
    started = models.BooleanField(default=False)

    class Meta:
        db_table = 'proxy'


class TestRunning(models.Model):
    '''Model for the running test'''
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    result_file_dest = models.CharField(max_length=200, default="")
    monitoring_file_dest = models.CharField(max_length=200, default="")
    log_file_dest = models.CharField(max_length=200, default="")
    display_name = models.CharField(max_length=100, default="")
    start_time = models.BigIntegerField()
    pid = models.IntegerField(default=0)
    jmeter_remote_instances = JSONField(null=True, blank=True)
    workspace = models.CharField(max_length=200, default="")
    is_running = models.BooleanField(default=False)
    build_number = models.IntegerField(default=0)
    duration = models.IntegerField(default=0)


    class Meta:
        db_table = 'test_running'


class LoadGeneratorServer(models.Model):
    address = models.CharField(max_length=200, default="")
    ssh_key = models.ForeignKey(SSHKey, on_delete=models.CASCADE,null=True, blank=True)
    class Meta:
        db_table = 'load_generator_server'

class LoadGenerator(models.Model):
    hostname = models.CharField(max_length=200, default="")
    num_cpu = models.CharField(max_length=200, default="")
    memory = models.CharField(max_length=200, default="")
    memory_free = models.CharField(max_length=200, default="")
    la_1 = models.CharField(max_length=200, default="")
    la_5 = models.CharField(max_length=200, default="")
    la_15 = models.CharField(max_length=200, default="")
    status = models.CharField(max_length=200, default="")
    reason = models.CharField(max_length=200, default="")
    class Meta:
        db_table = 'load_generator'
        

class JmeterInstance(models.Model):
    test_running = models.ForeignKey(TestRunning, on_delete=models.CASCADE)
    load_generator = models.ForeignKey(LoadGenerator)
    pid = models.IntegerField(default=0)
    port = models.IntegerField(default=0)
    jmeter_dir = models.CharField(max_length=300, default="")
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    threads_number = models.IntegerField(default=0)
    class Meta:
        db_table = 'jmeter_instance'

class JmeterInstanceStatistic(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    data = JSONField()
    class Meta:
        db_table = 'jmeter_instance_statistic'

class JMeterTestPlanParameter(models.Model):
    p_name = models.CharField(max_length=200, default="")

    class Meta:
        db_table = 'jmeter_parameter'


class ScriptParameter(models.Model):
    p_name = models.CharField(max_length=200, default="")

    class Meta:
        db_table = 'script_parameter'
