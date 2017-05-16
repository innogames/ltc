from __future__ import unicode_literals
from analyzer.models import Project
from django.contrib.postgres.fields import JSONField
from django.db import models

# Create your models here.

class Proxy(models.Model):
	port = models.IntegerField(default=0)
	pid = models.IntegerField(default=0)
	destination = models.CharField(max_length=200, default="https://dest")
	delay = models.FloatField()
	started = models.BooleanField(default=False)

	class Meta:
		db_table = 'proxy'


class TestRunning(models.Model):
	project = models.ForeignKey(Project, on_delete=models.CASCADE)
	result_file_dest = models.CharField(max_length=200, default = "")
	log_file_dest = models.CharField(max_length=200, default = "")
	display_name = models.CharField(max_length=100, default = "")
	start_time = models.BigIntegerField()
	pid = models.IntegerField(default=0)
	jmeter_remote_instances = JSONField(null=True, blank=True)
	workspace = models.CharField(max_length=200, default = "")
	class Meta:
		db_table = 'test_running'


class LoadGeneratorServer(models.Model):
	address = models.CharField(max_length=200, default = "")

	class Meta:
		db_table = 'load_generator_server'


class JMeterTestPlanParameter(models.Model):
	p_name = models.CharField(max_length=200, default = "")
	class Meta:
		db_table = 'jmeter_parameter'


class ScriptParameter(models.Model):
	p_name = models.CharField(max_length=200, default = "")
	class Meta:
		db_table = 'script_parameter'