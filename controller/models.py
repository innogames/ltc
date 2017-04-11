from __future__ import unicode_literals
from analyzer.models import Project
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
	result_file_path = models.CharField(max_length=200, default = "")
	display_name = models.CharField(max_length=100, default = "")
	start_time = models.BigIntegerField()
	pid = models.IntegerField(default=0)

	class Meta:
		db_table = 'test_running'