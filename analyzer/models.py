from __future__ import unicode_literals

import dataclasses
import json

from django.contrib import admin
from django.contrib.postgres.fields import JSONField
from django.core import serializers
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import Avg, FloatField, Func, Max, Min, Sum
from django.db.models.expressions import F, RawSQL
from django.apps import apps
# Create your models here.
from administrator.models import JMeterProfile, User


class Round(Func):
    function = 'ROUND'
    template = '%(function)s(%(expressions)s, 1)'


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

    def get_test_metric(self, metric):

        metrics = {
            'mean':
            {'query':
                Sum(RawSQL("((data->>%s)::numeric)", ('avg',)) *
                    RawSQL("((data->>%s)::numeric)", ('count',))) /
                Sum(RawSQL("((data->>%s)::numeric)", ('count',))),
                'source_model': 'TestData'
                },
            'median':
            {'query':
                Sum(RawSQL("((data->>%s)::numeric)", ('median',)) *
                    RawSQL("((data->>%s)::numeric)", ('count',))) /
                Sum(RawSQL("((data->>%s)::numeric)", ('count',))),
                'source_model': 'TestData'
             },
            'cpu_load':
            {
                'query': Avg(RawSQL(
                    "((data->>%s)::float) + ((data->>%s)::float) + "
                    "((data->>%s)::float)", (
                        'CPU_user',
                        'CPU_iowait',
                        'CPU_system',
                    ))),
                'source_model': 'ServerMonitoringData'
            }

        }

        metric_mapping = {
                metric: metrics[metric]['query']
        }
        source_model = metrics[metric]['source_model']
        model_class = apps.get_model(
            'analyzer', source_model
        )

        data = model_class.objects.filter(
            test__id=self.id, source='default', data_resolution_id=1
        )
        data = data.annotate(
            start_time=F('test__start_time')
        )

        data = data.values('start_time').annotate(
            **metric_mapping
        )
        #TODO: think about it
        if metric == 'cpu_load':
            data = data.values(metric, 'server__server_name')
        else:
            data = data.values(metric)
        data = data.order_by('start_time')
        return list(data)


    def aggregate_table(self):
        '''Return aggregate data for the test'''

        return TestActionAggregateData.objects.annotate(
            url=F('action__url')
        ).filter(test_id=self.id).values('url', 'action_id', 'data')


    def top_errors(self, n=5):
        '''
        Return top N actions with highest errors percentage
        '''

        data = TestActionAggregateData.objects.filter(test_id=self.id). \
            annotate(url=F('action__url')). \
            annotate(errors=Round(
                RawSQL("((data->>%s)::numeric)", ('errors',)) * 100 /
                RawSQL("((data->>%s)::numeric)", ('count',)))
        ).order_by('-errors').values('url', 'action_id', 'errors')[:n]
        return data

    def top_mean(self, n=10):
        '''
        Return top N actions with highest average response times
        '''

        data = TestActionAggregateData.objects.filter(
            test_id=self.id
        ).annotate(url=F('action__url')).annotate(
            average=RawSQL("((data->>%s)::numeric)", ('mean',))
        ).order_by('-average').values('url', 'average')[:n]
        data = json.dumps(list(data), cls=DjangoJSONEncoder)
        return data

    def __str__(self):
        return self.display_name

    def prev_test(self):
        '''
        Return previous for the current test
        '''

        t = Test.objects.filter(
            start_time__lte=self.start_time, project=self.project
        ).order_by('-start_time')[:2]
        if len(t) > 1:
            return t[1]
        return self


class TestData(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    data_resolution = models.ForeignKey(
        TestDataResolution, on_delete=models.CASCADE, default=1
    )
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
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
    error = models.ForeignKey(Error, on_delete=models.CASCADE)
    count = models.IntegerField(default=0)

    class Meta:
        db_table = 'test_error'


class TestActionData(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    data_resolution = models.ForeignKey(
        TestDataResolution, on_delete=models.CASCADE,
        default=1
    )
    action = models.ForeignKey(
        Action, on_delete=models.CASCADE, null=True, blank=True
    )
    data = JSONField()

    class Meta:
        db_table = 'test_action_data'
        index_together = [
            ('test', 'action', 'data_resolution'),
        ]


class TestAggregate(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    data = JSONField()

    class Meta:
        db_table = 'test_aggregate'


class TestActionAggregateData(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
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
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    data_resolution = models.ForeignKey(
        TestDataResolution, on_delete=models.CASCADE, default=1
    )
    source = models.CharField(max_length=100, default='default')
    server = models.ForeignKey(Server, on_delete=models.CASCADE)
    data = JSONField()

    class Meta:
        db_table = 'server_monitoring_data'
        index_together = [
            ('test', 'server', 'source', 'data_resolution'),
        ]


class TestResultFile(models.Model):
    #project = models.ForeignKey(Project, on_delete=models.CASCADE, default=1)
    #test = models.ForeignKey(Test)
    file = models.FileField(upload_to='test_result_files/')

    #uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'test_result_file'
