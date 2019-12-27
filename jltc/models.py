import datetime
import json
import logging
import math
import os
import re
import tempfile
import zipfile
from collections import OrderedDict, defaultdict
from os.path import dirname as up
from xml.etree.ElementTree import ElementTree

import numpy as np
import pandas as pd
from django.apps import apps
from django.db import models
from django.db.models import Avg, FloatField, Func, Max, Min, Sum
from django.db.models.expressions import F, RawSQL
from pandas import DataFrame

from analyzer.models import (Action, TestActionAggregateData, TestActionData,
                             TestData, TestDataResolution)
from controller.models import JmeterServerData
from controller.utils import jmeter_simple_writer

logger = logging.getLogger(__name__)

dateconv = np.vectorize(datetime.datetime.fromtimestamp)


class Round(Func):
    function = 'ROUND'
    template = '%(function)s(%(expressions)s, 1)'


class Configuration(models.Model):
    name = models.TextField()
    value = models.TextField()
    description = models.TextField()

    def __str__(self):
        return self.name


class Project(models.Model):
    name = models.TextField()
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def get_thread_malloc(self):
        """Return avg memory allocation per thread for the current project

        Returns:
            int: MB
        """

        max_threads = JmeterServerData.objects.filter(
            project=self
        ).annotate(
            threads=RawSQL("((data->>%s)::numeric)",
            ('threads_number',))
        ).aggregate(max_threads=Max(
                F('threads'), output_field=FloatField()
            )
        )

        data = JmeterServerData.objects.filter(
            project=self, data__contains=[{'threads_number': max_threads}]
        ).annotate(mem_per_thread=(
                RawSQL("((data->>%s)::numeric)", ('S0U',)) +
                RawSQL("((data->>%s)::numeric)", ('S1U',)) +
                RawSQL("((data->>%s)::numeric)", ('EU',)) +
                RawSQL("((data->>%s)::numeric)", ('OU',))
            )/1024/RawSQL("((data->>%s)::numeric)", ('threads_number',))
        ).aggregate(thread_malloc=Avg(
                F('thread_malloc'), output_field=FloatField()
            )
        )
        thread_malloc = int(math.ceil(data['thread_malloc']))
        logger.info('Estimated malloc (MB) per thread: %s', thread_malloc)
        return thread_malloc

class Test(models.Model):
    CREATED = 'C'
    RUNNING = 'R'
    ANALYZING = 'A'
    FINISHED = 'F'
    STATUSES = (
        (CREATED, 'created'),
        (RUNNING, 'running'),
        (ANALYZING, 'analyzing'),
        (FINISHED, 'finished'),
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True)
    name = models.TextField(default='')
    status = models.CharField(
        max_length=12, choices=STATUSES, default=CREATED
    )
    threads = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, db_index=True)
    finished_at = models.DateTimeField(null=True, db_index=True)

    def __str__(self):
        return self.name

    def prev_test(self):
        '''
        Return previous for the current test
        '''

        t = Test.objects.filter(
            started_at__lte=self.started_at, project=self.project
        ).order_by('-started_at')[:2]
        if len(t) > 1:
            return t[1]
        return self

    def analyze(self, mode=''):
        logger.info('Parse and generate test data: {}'.format(self.id))
        if self.status == Test.RUNNING:
            self.status = Test.ANALYZING
            self.save()
        for file in TestFile.objects.filter(test=self):
            file.generate_report()

    def init(self, source='jenkins_build'):
        data = TestFile.objects.get(
            test=self, file_type=TestFile.JENKINS_BUILD_XML
        ).test_metadata()
        self.name = data['name']
        self.status = data['status']
        self.project = data['project']
        self.started_at = data['started_at']
        self.finished_at = data['finished_at']
        self.save()

    def aggregate_table(self):
        '''Return aggregate data for the test'''

        return TestActionAggregateData.objects.annotate(
            name=F('action__name')
        ).filter(test=self).values('name', 'action_id', 'data')

    def top_errors(self, n=5):
        '''
        Return top N actions with highest errors percentage
        '''

        data = TestActionAggregateData.objects.filter(test=self). \
            annotate(name=F('action__name')). \
            annotate(errors=Round(
                RawSQL("((data->>%s)::numeric)", ('errors',)) * 100 /
                RawSQL("((data->>%s)::numeric)", ('count',)))
        ).order_by('-errors').values('name', 'action_id', 'errors')[:n]
        return data

    def top_mean(self, n=10):
        '''
        Return top N actions with highest average response times
        '''

        data = TestActionAggregateData.objects.filter(
            test=self).annotate(name=F('action__name')).annotate(
            mean=RawSQL("((data->>%s)::numeric)", ('mean',))
        ).order_by('-mean').values('name', 'mean')[:n]
        data = json.dumps(list(data), cls=DjangoJSONEncoder)
        return data

    def get_test_metric(self, metric):

        metrics = {
            'mean':
            {'query':
                Sum(RawSQL("((data->>%s)::numeric)", ('mean',)) *
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
            test=self, source='default', data_resolution_id=1
        )
        data = data.annotate(
            started_at=F('test__started_at')
        )

        data = data.values('started_at').annotate(
            **metric_mapping
        )
        # TODO: think about it
        if metric == 'cpu_load':
            data = data.values(metric, 'server__server_name')
        else:
            data = data.values(metric)
        data = data.order_by('started_at')
        return list(data)

    def prepare_test_plan(self):
        """Prepares test plan by adding Jmeter Simple CSV write at the end of
        .jmx file
        """

        testplan = TestFile.objects.filter(
            test=self, file_type=TestFile.TESTPLAN_FILE
        ).first()
        result_file = TestFile.objects.filter(
            test=self, file_type=TestFile.MAIN_RESULT_CSV_FILE
        ).first()
        if testplan:
            with open(testplan.path, 'r') as src_jmx:
                source_lines = src_jmx.readlines()
                closing = source_lines.pop(-1)
                closing = source_lines.pop(-1) + closing
                if "<hashTree/>" in source_lines[-1]:
                    source_lines.pop(-1)
                    source_lines.pop(-1)
                    source_lines.pop(-1)
                    source_lines.pop(-1)
                closing = source_lines.pop(-1) + closing
                fd, fname = tempfile.mkstemp('.jmx', 'new_')
                os.close(fd)
                os.chmod(fname, 644)
                # Destination of test plan
                testplan.path = fname
                file_handle = open(testplan.path, "w")
                logger.info('New testplan: %s', testplan.path)
                file_handle.write(''.join(source_lines))
                file_handle.write(
                    ''.join(jmeter_simple_writer(result_file)))
                file_handle.write(closing)
                file_handle.close()
        return testplan.save()


    def find_loadgenerators(self):
        THREAD_COUNT_CONFIG = {
            1: 400,
            2: 400,
            3: 300,
            4: 300,
            5: 200,
            6: 200,
        }
        thread_malloc = self.project.get_thread_malloc()
        threads_per_jmeter_server = THREAD_COUNT_CONFIG.get(thread_malloc, 100)
        logger.info(
            'Estimated threads per Jmeter server: %s',
            threads_per_jmeter_server
        )
        jmeter_servers_count = int(math.ceil(float(self.threads) /
                                             threads_per_jmeter_server)
        )
        jmeter_server_malloc = int(math.ceil(
            thread_malloc * threads_per_jmeter_server * 1.2
        ))
        malloc_total = math.ceil(
            jmeter_servers_count * jmeter_server_malloc
        )
        jmeter_servers_per_loadgenerator = {}
        for loadgenerator in LoadGenerator.objects.all():
            jmeter_servers_per_loadgenerator[
                loadgenerator.hostname
            ] = math.ceil(loadgenerator.memory_free/(jmeter_server_malloc))
        loadgenerators = sorted(
            jmeter_servers_per_loadgenerator,
            key=jmeter_servers_per_loadgenerator.get,
            reverse=True
        )


class TestFile(models.Model):
    ONLINE_RESULT_CSV_FILE = 'O'
    MAIN_RESULT_CSV_FILE = 'M'
    LOG_FILE = 'L'
    TESTPLAN_FILE = 'T'
    JENKINS_BUILD_XML = 'J'
    TYPES = (
        (ONLINE_RESULT_CSV_FILE, 'online_result'),
        (MAIN_RESULT_CSV_FILE, 'result'),
        (LOG_FILE, 'log'),
        (TESTPLAN_FILE, 'testplan'),
        (JENKINS_BUILD_XML, 'jenkins_build_xml')
    )
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    path = models.TextField()
    file_type = models.CharField(
        max_length=12, choices=TYPES, default=MAIN_RESULT_CSV_FILE
    )
    file_size = models.IntegerField(default=0)
    last_analyzed = models.DateTimeField(default=None, null=True)
    last_analyzed_line = models.IntegerField(default=0)

    def archive(self):
        archive_path = self.path + '.zip'
        if os.path.exists(archive_path):
            os.remove(archive_path)

        logger.info('Move results file ' + self.path + ' to zip archive.')
        with zipfile.ZipFile(
            self.path + '.zip', 'w', zipfile.ZIP_DEFLATED,
            allowZip64=True
        ) as zip_file:
            zip_file.write(self.path, os.path.basename(self.path))
        os.remove(self.path)
        logger.info('File was packed, original file was deleted.')

    def generate_report(self):
        if self.file_type == TestFile.MAIN_RESULT_CSV_FILE:
            self.parse_csv()

    def test_metadata(self):
        data = self.parse_build_xml()
        return data

    def parse_build_xml(self):
        """Parse Jenkins build.xml file and create test object

        Returns:
            test: test object
        """

        build_xml = ElementTree()
        build_parameters = []
        display_name = 'unknown'

        if os.path.isfile(self.path):
            build_xml.parse(self.path)
            build_tag = build_xml.getroot()

            for params in build_tag:
                if params.tag == 'actions':
                    parameters = params.find('.//parameters')
                    for parameter in parameters:
                        name = parameter.find('name')
                        value = parameter.find('value')
                        build_parameters.append([name.text, value.text])
                elif params.tag == 'startTime':
                    start_time = int(params.text)/1000
                elif params.tag == 'duration':
                    duration = int(params.text)
                elif params.tag == 'displayName':
                    display_name = params.text
        project_name = os.path.basename(up(up(up(self.path))))
        build_number = os.path.basename(up(self.path))
        project, created = Project.objects.get_or_create(
            name=project_name
        )
        data = {
            'name': display_name,
            'project': project,
            'status': Test.RUNNING,
            'started_at': datetime.datetime.fromtimestamp(start_time),
            'finished_at': datetime.datetime.fromtimestamp(
                start_time + duration
            ),
        }
        logger.debug('Parsed build.xml test data {}.'.format(data))
        return data

    def parse_csv(self, data_resolution='1Min', csv_file_fields=[]):
        """Parse Jmeter .csv result file and put aggregate data to database.

        Args:
            data_resolution (str, optional): Data resolution
            to keep in database. Defaults to '1Min'.
            csv_file_fields (list, optional): CSV-file Header  Defaults to [].
        """

        if not os.path.exists(self.path):
            logger.error('File {} does not exists'.format(self.path))
            return

        data_resolution_id = TestDataResolution.objects.get(
            frequency=data_resolution).id

        if not csv_file_fields:
            csv_file_fields = [
                'response_time', 'url', 'responseCode', 'success',
                'threadName',
                'failureMessage', 'grpThreads', 'allThreads'
            ]

        df = pd.DataFrame()
        if os.stat(self.path).st_size > 1000007777:
            logger.debug("Executing a parse for a huge file")
            chunks = pd.read_table(
                self.path, sep=',', index_col=0, chunksize=3000000
            )
            for chunk in chunks:
                chunk.columns = csv_file_fields.split(',')
                chunk = chunk[~chunk['URL'].str.contains('exclude_')]
                df = df.append(chunk)
        else:
            df = pd.read_csv(
                self.path, index_col=0, low_memory=False
            )
            df.columns = csv_file_fields
            df = df[~df['url'].str.contains('exclude_', na=False)]
        self.archive()
        df.columns = csv_file_fields
        df.index = pd.to_datetime(dateconv((df.index.values / 1000)))
        num_lines = df['response_time'].count()
        logger.debug('Number of lines in file: {}'.format(num_lines))
        unique_urls = df['url'].unique()
        for url in unique_urls:
            action, created = Action.objects.get_or_create(
                name=str(url),
                project=self.test.project
            )
            if TestActionData.objects.filter(
                action=action,
                test=self.test,
                data_resolution_id=data_resolution_id
            ).exists():
                logger.warning(
                    '{} data for test {} exists, skipping.'.format(
                        action.name, self.test.name
                    )
                )
                continue
            logger.info("Adding action data: {}".format(action.name))
            df_url = df[(df.url == action.name)]
            url_data = pd.DataFrame()
            df_url_gr_by_ts = df_url.groupby(
                pd.Grouper(freq=data_resolution))
            url_data['mean'] = df_url_gr_by_ts.response_time.mean()
            url_data['median'] = df_url_gr_by_ts.response_time.median()
            url_data['count'] = df_url_gr_by_ts.success.count()
            df_url_gr_by_ts_only_errors = df_url[(
                df_url.success == False
            )].groupby(pd.Grouper(freq=data_resolution))
            url_data[
                'errors'] = df_url_gr_by_ts_only_errors.success.count()
            url_data['test_id'] = self.test.id
            url_data['name'] = action.name
            output_json = json.loads(
                url_data.to_json(orient='index', date_format='iso'),
                object_pairs_hook=OrderedDict
            )
            for row in output_json:
                data = {
                    'timestamp': row,
                    'mean': output_json[row]['mean'],
                    'median': output_json[row]['median'],
                    'count': output_json[row]['count'],
                    'name': output_json[row]['name'],
                    'errors': output_json[row]['errors'],
                    'test_id': output_json[row]['test_id'],
                }
                test_action_data = TestActionData(
                    test=self.test,
                    action=action,
                    data_resolution_id=data_resolution_id,
                    data=data)
                test_action_data.save()

            if not TestActionAggregateData.objects.filter(
                action=action, test=self.test
            ).exists():
                url_agg_data = dict(
                    json.loads(df_url['response_time'].describe().to_json())
                )
                url_agg_data['99%'] = float(
                    df_url['response_time'].quantile(.99)
                )
                url_agg_data['90%'] = float(
                    df_url['response_time'].quantile(.90)
                )
                url_agg_data['weight'] = float(
                    df_url['response_time'].sum())
                url_agg_data['errors'] = float(df_url[(
                    df_url['success'] == False)]['success'].count())
                test_action_aggregate_data = TestActionAggregateData(
                    test=self.test,
                    action=action,
                    data=url_agg_data
                )
                test_action_aggregate_data.save()

        if not TestData.objects.filter(
            test=self.test,
            data_resolution_id=data_resolution_id
        ).exists():
            test_overall_data = pd.DataFrame()
            df_gr_by_ts = df.groupby(pd.Grouper(freq=data_resolution))
            test_overall_data['mean'] = df_gr_by_ts.response_time.mean()
            test_overall_data['median'] = df_gr_by_ts.response_time.median()
            test_overall_data['count'] = df_gr_by_ts.response_time.count()
            test_overall_data['test_id'] = self.test.id
            output_json = json.loads(
                test_overall_data.to_json(orient='index', date_format='iso'),
                object_pairs_hook=OrderedDict
            )
            for row in output_json:
                data = {
                    'timestamp': row,
                    'mean': output_json[row]['mean'],
                    'median': output_json[row]['median'],
                    'count': output_json[row]['count']
                }
                test_data = TestData(
                    test=self.test,
                    data_resolution_id=data_resolution_id,
                    data=data
                )
                test_data.save()
