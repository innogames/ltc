import json

from django.contrib import admin
from django.apps import apps
from django.contrib.postgres.fields import JSONField
from django.core import serializers
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import Avg, FloatField, Func, Max, Min, Sum
from django.db.models.expressions import F, RawSQL
from django.apps import apps


class TestDataResolution(models.Model):
    frequency = models.CharField(max_length=100)
    per_sec_divider = models.IntegerField(default=60)

    def __str__(self):
        return self.frequency

class TestData(models.Model):
    test = models.ForeignKey(to='jltc.Test', on_delete=models.CASCADE)
    data_resolution = models.ForeignKey(
        TestDataResolution, on_delete=models.CASCADE, default=1
    )
    source = models.CharField(max_length=100, default='default')
    data = JSONField()


class Action(models.Model):
    name = models.TextField()
    project = models.ForeignKey(
        to='jltc.Project', on_delete=models.CASCADE, default=1)
    description = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = (('name', 'project'))


class Error(models.Model):
    text = models.TextField(db_index=True)
    code = models.CharField(max_length=400, null=True, blank=True)


class TestError(models.Model):
    test = models.ForeignKey(to='jltc.Test', on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
    error = models.ForeignKey(Error, on_delete=models.CASCADE)
    count = models.IntegerField(default=0)


class TestActionData(models.Model):
    test = models.ForeignKey(to='jltc.Test', on_delete=models.CASCADE)
    data_resolution = models.ForeignKey(
        TestDataResolution, on_delete=models.CASCADE,
        default=1
    )
    action = models.ForeignKey(
        Action, on_delete=models.CASCADE, null=True, blank=True
    )
    data = JSONField()

    class Meta:
        index_together = [
            ('test', 'action', 'data_resolution'),
        ]


class TestActionAggregateData(models.Model):
    test = models.ForeignKey(to='jltc.Test', on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
    data = JSONField()

    class Meta:
        index_together = [
            ('test', 'action'),
        ]


class Server(models.Model):
    server_name = models.TextField()
    description = models.TextField()


class ServerMonitoringData(models.Model):
    test = models.ForeignKey(to='jltc.Test', on_delete=models.CASCADE)
    data_resolution = models.ForeignKey(
        TestDataResolution, on_delete=models.CASCADE, default=1
    )
    source = models.TextField(default='default')
    server = models.ForeignKey(Server, on_delete=models.CASCADE)
    data = JSONField()

    class Meta:
        index_together = [
            ('test', 'server', 'source', 'data_resolution'),
        ]
