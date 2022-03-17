from __future__ import unicode_literals

import datetime
import json
import logging
import os
import random
import re
from collections import OrderedDict
import pandas as pd
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models.fields import related
from ltc.base.models import Test, TestFile
from pylab import *
from pylab import np

dateconv = np.vectorize(datetime.datetime.fromtimestamp)
logger = logging.getLogger('django')

class TestOnlineData(models.Model):
    test = models.ForeignKey(
        Test, on_delete=models.CASCADE,
        related_name='online_data'
    )
    name = models.CharField(max_length=200, default='')
    start_line = models.IntegerField(default=0)
    data = JSONField()

    @classmethod
    def update(cls, test: Test):
        try:
            if test.is_locked is True:
                return
            test.is_locked = True
            test.save()
            result_file = TestFile.objects.filter(
                test=test,
                file_type=TestFile.MAIN_RESULT_CSV_FILE,
            ).first()
            if not result_file:
                return
            result_file_path = str(result_file.path)
            logger.info(f'[online] result file X{result_file_path}X')
            logger.info(os.access(result_file_path, os.F_OK))
            logger.info(os.access(result_file_path, os.F_OK))
            if not os.path.exists(result_file_path):
                logger.info(
                    f'[online] result file does not exists X{result_file_path}X'
                )
                test.is_locked = False
                test.save()
                return
            num_lines = sum(1 for line in open(result_file_path))
            if test.online_lines_analyzed > num_lines - 10:
                test.is_locked = False
                test.save()
                return
            read_lines = num_lines - test.online_lines_analyzed - 10
            skiprows = test.online_lines_analyzed
            df = pd.read_csv(
                result_file_path,
                index_col=0,
                low_memory=False,
                skiprows=skiprows,
                nrows=read_lines
            )
            test.online_lines_analyzed = (skiprows + read_lines)
            test.save()
            df.columns = [
                'response_time', 'url', 'responseCode', 'success',
                'threadName', 'failureMessage', 'grpThreads', 'allThreads'
            ]
            df.index = pd.to_datetime(dateconv((df.index.values / 1000)))

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

            if not TestOnlineData.objects.filter(
                test=test,
                name='response_codes'
            ).exists():
                online_data = TestOnlineData(
                    test=test,
                    name='response_codes',
                    data=new_data
                )
                online_data.save()
            else:
                online_data = TestOnlineData.objects.get(
                    test=test, name='response_codes'
                )
                old_data = online_data.data
                for k in new_data:
                    if k not in old_data:
                        old_data[k] = {'count': 0}
                    old_data[k] = {
                        'count': old_data[k]['count'] + new_data[k]['count']
                    }
                online_data.data = old_data
                online_data.save()

            # Aggregate table
            update_df = pd.DataFrame()
            group_by_url = df.groupby('url')
            update_df = group_by_url.aggregate({
                'response_time': np.mean
            }).round(1)
            update_df['maximum'] = group_by_url.response_time.max().round(1)
            update_df['minimum'] = group_by_url.response_time.min().round(1)
            update_df['count'] = group_by_url.success.count().round(1)
            update_df['errors'] = df[(
                df.success == False
            )].groupby('url')['success'].count()
            update_df['weight'] = group_by_url.response_time.sum()
            update_df = update_df.fillna(0)
            update_df.columns = [
                'average',
                'maximum',
                'minimum',
                'count',
                'errors',
                'weight'
            ]
            new_data = {}
            output_json = json.loads(
                update_df.to_json(orient='index', date_format='iso'),
                object_pairs_hook=OrderedDict
            )
            for row in output_json:
                new_data[row] = {
                    'average': output_json[row]['average'],
                    'maximum': output_json[row]['maximum'],
                    'minimum': output_json[row]['minimum'],
                    'count': output_json[row]['count'],
                    'errors': output_json[row]['errors'],
                    'weight': output_json[row]['weight']
                }
            if not TestOnlineData.objects.filter(
                test=test,
                name='aggregate_table'
            ).exists():
                online_data = TestOnlineData(
                    test=test,
                    name='aggregate_table',
                    data=new_data)
                online_data.save()
            else:
                online_data = TestOnlineData.objects.get(
                    test=test,
                    name='aggregate_table'
                )
                old_data = online_data.data
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
                    maximum = (
                        new_data[k]['maximum']
                        if new_data[k]['maximum'] > old_data[k]['maximum']
                        else old_data[k]['maximum']
                    )
                    minimum = (
                        new_data[k]['minimum']
                        if new_data[k]['minimum'] < old_data[k]['minimum']
                        else old_data[k]['minimum']
                    )
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
                online_data.data = old_data
                online_data.save()

            # Over time data
            update_df = pd.DataFrame()
            df_gr_by_ts = df.groupby(pd.Grouper(freq='1Min'))
            update_df['avg'] = df_gr_by_ts.response_time.mean()
            update_df['count'] = df_gr_by_ts.success.count()
            update_df['weight'] = df_gr_by_ts.response_time.sum()
            df_gr_by_ts_only_errors = df[(
                df.success == False)].groupby(pd.Grouper(freq='1Min'))
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
                if not TestOnlineData.objects.filter(
                    test=test,
                    name='data_over_time'
                ).exists():
                    online_data = TestOnlineData(
                        test=test,
                        name='data_over_time',
                        data=new_data
                    )
                    online_data.save()
                else:
                    data_over_time_data = TestOnlineData.objects.filter(
                        test=test,
                        name='data_over_time'
                    ).values()
                    update = False
                    for d in data_over_time_data:
                        if d['data']['timestamp'] == new_data['timestamp']:
                            d_id = d['id']
                            update = True
                    if update:
                        test_running_data = TestOnlineData.objects.get(
                            id=d_id
                        )
                        old_data = test_running_data.data
                        old_data['average'] = (
                            old_data['weight'] + new_data['weight']) / (
                                old_data['count'] + new_data['count'])
                        old_data[
                            'count'] = old_data['count'] + new_data['count']
                        old_errors = (
                            0 if old_data['errors'] is None
                            else old_data['errors']
                        )
                        new_errors = (
                            0 if new_data['errors'] is None
                            else new_data['errors']
                        )
                        old_data[
                            'errors'] = old_errors + new_errors
                        old_data['weight'] = (
                            old_data['weight'] + new_data['weight']
                        )
                        test_running_data.data = old_data
                        test_running_data.save()
                    else:
                        test_running_data = TestOnlineData(
                            test=test,
                            name='data_over_time',
                            data=new_data)
                        test_running_data.save()
            test.is_locked = False
            test.save()
        except Exception as e:
            test.is_locked = False
            test.save()
