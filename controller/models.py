from __future__ import unicode_literals
import datetime
import json
from analyzer.models import Project
from django.contrib.postgres.fields import JSONField
from django.db import models
import pandas as pd
from collections import defaultdict, OrderedDict
# Create your models here.
from administrator.models import SSHKey
from pylab import np

dateconv = np.vectorize(datetime.datetime.fromtimestamp)


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
    result_start_line = models.IntegerField(default=0)
    result_file_size = models.IntegerField(default=0)

    def update_data_frame(self):
        num_lines = sum(1 for line in open(self.result_file_dest))
        if self.result_start_line < num_lines - 10:
            read_lines = num_lines - self.result_start_line - 10
            df = pd.read_csv(
                self.result_file_dest,
                index_col=0,
                low_memory=False,
                skiprows=self.result_start_line,
                nrows=read_lines)

            df.columns = [
                'response_time', 'URL', 'responseCode', 'success',
                'threadName', 'failureMessage', 'grpThreads', 'allThreads'
            ]

            df = df[~df['URL'].str.contains('exclude_')]
            df.index = pd.to_datetime(dateconv((df.index.values / 1000)))
            # update start line for the next parse
            self.result_start_line = self.result_start_line + read_lines

            ### Response Codes
            group_by_response_codes = df.groupby('responseCode')
            update_df = pd.DataFrame()
            update_df['count'] = group_by_response_codes.success.count()
            update_df = update_df.fillna(0)
            output_json = json.loads(
                update_df.to_json(orient='index', date_format='iso'),
                object_pairs_hook=OrderedDict)
            new_data = {}
            for row in output_json:
                new_data[row] = {'count': output_json[row]['count']}

            if not TestRunningData.objects.filter(
                    test_running_id=self.id, name="response_codes").exists():
                test_running_data = TestRunningData(
                    test_running_id=self.id,
                    name="response_codes",
                    data=new_data)
                test_running_data.save()
            else:
                data = {}
                test_running_data = TestRunningData.objects.get(
                    test_running_id=self.id, name="response_codes")
                old_data = test_running_data.data
                for k in new_data:
                    if k not in old_data:
                        old_data[k] = {'count': 0}
                    old_data[k] = {
                        'count': old_data[k]['count'] + new_data[k]['count']
                    }
                test_running_data.data = old_data
                test_running_data.save()

            ### Aggregate table
            update_df = pd.DataFrame()
            group_by_url = df.groupby('URL')
            update_df = group_by_url.aggregate({
                'response_time': np.mean
            }).round(1)
            update_df['maximum'] = group_by_url.response_time.max().round(1)
            update_df['minimum'] = group_by_url.response_time.min().round(1)
            update_df['count'] = group_by_url.success.count().round(1)
            update_df['errors'] = df[(
                df.success == False)].groupby('URL')['success'].count()
            update_df['weight'] = group_by_url.response_time.sum()
            update_df = update_df.fillna(0)
            update_df.columns = [
                'average', 'maximum', 'minimum', 'count', 'errors', 'weight'
            ]
            new_data = {}
            output_json = json.loads(
                update_df.to_json(orient='index', date_format='iso'),
                object_pairs_hook=OrderedDict)
            for row in output_json:
                new_data[row] = {
                    'average': output_json[row]['average'],
                    'maximum': output_json[row]['maximum'],
                    'minimum': output_json[row]['minimum'],
                    'count': output_json[row]['count'],
                    'errors': output_json[row]['errors'],
                    'weight': output_json[row]['weight']
                }
            if not TestRunningData.objects.filter(
                    test_running_id=self.id, name="aggregate_table").exists():
                test_running_data = TestRunningData(
                    test_running_id=self.id,
                    name="aggregate_table",
                    data=new_data)
                test_running_data.save()
            else:
                data = {}
                test_running_data = TestRunningData.objects.get(
                    test_running_id=self.id, name="aggregate_table")
                old_data = test_running_data.data
                for k in new_data:
                    if k not in old_data:
                        old_data[k] = {
                            'average': 0,
                            'maximum': 0,
                            'minimum': 0,
                            'count': 0,
                            'errors': 0,
                            'weight': 0
                        }
                    maximum = new_data[k][
                        'maximum'] if new_data[k]['maximum'] > old_data[k]['maximum'] else old_data[
                            k]['maximum']
                    minimum = new_data[k][
                        'minimum'] if new_data[k]['minimum'] < old_data[k]['minimum'] else old_data[
                            k]['minimum']
                    old_data[k] = {
                        'average':
                        (old_data[k]['weight'] + new_data[k]['weight']) /
                        (old_data[k]['count'] + new_data[k]['count']),
                        'maximum':
                        maximum,
                        'minimum':
                        minimum,
                        'count':
                        old_data[k]['count'] + new_data[k]['count'],
                        'errors':
                        old_data[k]['errors'] + new_data[k]['errors'],
                        'weight':
                        old_data[k]['weight'] + new_data[k]['weight'],
                    }
                test_running_data.data = old_data
                test_running_data.save()

            ### Over time data
            update_df = pd.DataFrame()
            df_gr_by_ts = df.groupby(pd.TimeGrouper(freq='1Min'))
            update_df['avg'] = df_gr_by_ts.response_time.mean()
            update_df['count'] = df_gr_by_ts.success.count()
            update_df['weight'] = df_gr_by_ts.response_time.sum()
            df_gr_by_ts_only_errors = df[(
                df.success == False)].groupby(pd.TimeGrouper(freq='1Min'))
            update_df['errors'] = df_gr_by_ts_only_errors.success.count()
            new_data = {}
            output_json = json.loads(
                update_df.to_json(orient='index', date_format='iso'),
                object_pairs_hook=OrderedDict)

            for row in output_json:
                new_data = {
                    'timestamp': row,
                    'avg': output_json[row]['avg'],
                    'count': output_json[row]['count'],
                    'errors': output_json[row]['errors'],
                    'weight': output_json[row]['weight'],
                }
                if not TestRunningData.objects.filter(
                        test_running_id=self.id,
                        name="data_over_time").exists():
                    test_running_data = TestRunningData(
                        test_running_id=self.id,
                        name="data_over_time",
                        data=new_data)
                    test_running_data.save()
                else:
                    data_over_time_data = TestRunningData.objects.filter(
                        test_running_id=self.id,
                        name="data_over_time").values()
                    update = False
                    for d in data_over_time_data:
                        if d['data']['timestamp'] == new_data['timestamp']:
                            d_id = d['id']
                            update = True
                    if update:
                        test_running_data = TestRunningData.objects.get(
                            id=d_id)
                        old_data = test_running_data.data
                        old_data['average'] = (
                            old_data['weight'] + new_data['weight']) / (
                                old_data['count'] + new_data['count'])
                        old_data[
                            'count'] = old_data['count'] + new_data['count']
                        if new_data['errors'] is not None:
                            old_data[
                                'errors'] = old_data['errors'] + new_data['errors']
                        old_data[
                            'weight'] = old_data['weight'] + new_data['weight']
                        test_running_data.data = old_data
                        test_running_data.save()
                    else:
                        test_running_data = TestRunningData(
                        test_running_id=self.id,
                        name="data_over_time",
                        data=new_data)
                        test_running_data.save()
            self.save()

    class Meta:
        db_table = 'test_running'


class TestRunningData(models.Model):
    test_running = models.ForeignKey(TestRunning, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, default="")
    data = JSONField()

    class Meta:
        db_table = 'test_running_data'


class LoadGeneratorServer(models.Model):
    address = models.CharField(max_length=200, default="")
    ssh_key = models.ForeignKey(
        SSHKey, on_delete=models.CASCADE, null=True, blank=True)

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
