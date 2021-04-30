from __future__ import unicode_literals

from django.db import models
from django.contrib.postgres.fields import JSONField
from django.contrib import admin
# Create your models here.
from ltc.administrator.models import JMeterProfile, User


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
    confluence_page = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'project'

    def __str__(self):
        return self.project_name
