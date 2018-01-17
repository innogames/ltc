# -*- coding: utf-8 -*-
import json
import logging
import math
import time
import os

import numpy as na
from pylab import *
from collections import OrderedDict
from decimal import Decimal

from django import template
from django.db.models import Avg, FloatField, Max, Min, Sum
from django.db.models.expressions import F, RawSQL
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import TemplateView
from django.views import View
from django.urls import reverse

import pandas as pd
from administrator.models import Configuration
from analyzer.confluence import confluenceposter
from controller.views import update_test_graphite_data
from analyzer.confluence.utils import generate_confluence_graph
from models import (Action, Project, Server, ServerMonitoringData, Test,
                    TestActionAggregateData, TestActionData, TestData, Error,
                    TestError, TestResultFile)
from forms import TestResultFileUploadForm
from scipy import stats
from django.db.models import Func
from django.template.loader import render_to_string
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)
dateconv = np.vectorize(datetime.datetime.fromtimestamp)


class Round(Func):
    function = 'ROUND'
    template = '%(function)s(%(expressions)s, 1)'


def to_dict(result_proxy):
    fieldnames = []
    for fieldname in result_proxy.keys():
        fieldnames.append(fieldname)
    results = []
    for row in result_proxy.fetchall():
        results.append(OrderedDict(zip(fieldnames, row)))
    return results


def to_json(result_proxy, as_object):
    results = to_dict(result_proxy)
    if as_object:
        json_object = json.loads(
            json.dumps(results, sort_keys=False),
            object_pairs_hook=OrderedDict)
        return json_object
    else:
        json_string = json.dumps(
            results, sort_keys=False, default=str, indent=4)
        return json_string


def to_pivot(data, a, b, c):
    df = pd.DataFrame(data)
    df_pivot = pd.pivot_table(df, index=a, columns=b, values=c)
    return df_pivot


def upload_test_result_file(request):
    if request.method == 'GET':
        projects = Project.objects.values()
        return render(request, 'upload/test_result_file.html',
                      {'projects': projects})
    csv_file = request.FILES["csv_file"]
    csv_file_fields = request.POST.get('csv_file_fields', '1')
    test_name = request.POST.get('test_name', '1')
    project_id = int(request.POST.get('project_id', '0'))
    # Create new project
    if project_id == 0:
        project = Project(project_name="New project",)
        project.save()
        project_id = project.id
    test = Test(
        project_id=project_id,
        display_name=test_name,
        show=True,
        start_time=int(time.time() * 1000))
    test.save()
    test_id = test.id
    path = default_storage.save('test_result_data.csv',
                                ContentFile(csv_file.read()))
    jmeter_results_file = path
    if os.path.exists(jmeter_results_file):
        df = pd.DataFrame()
        if os.stat(jmeter_results_file).st_size > 1000007777:
            logger.debug("Executing a parse for a huge file")
            chunks = pd.read_table(
                jmeter_results_file, sep=',', index_col=0, chunksize=3000000)
            for chunk in chunks:
                chunk.columns = [csv_file_fields.split(',')]
                chunk = chunk[~chunk['URL'].str.contains('exclude_')]
                df = df.append(chunk)
        else:
            df = pd.read_csv(
                jmeter_results_file, index_col=0, low_memory=False)
            df.columns = [csv_file_fields.split(',')]
            df = df[~df['url'].str.contains('exclude_', na=False)]

        df.columns = [csv_file_fields.split(',')]

        df.index = pd.to_datetime(dateconv((df.index.values / 1000)))
        num_lines = df['response_time'].count()
        logger.debug('Number of lines in file: {}'.format(num_lines))
        unique_urls = df['url'].unique()
        for url in unique_urls:
            url = str(url)
            if not Action.objects.filter(
                    url=url, project_id=project_id).exists():
                logger.debug("Adding new action: " + str(url) + " project_id: "
                             + str(project_id))
                a = Action(url=url, project_id=project_id)
                a.save()
            a = Action.objects.get(url=url, project_id=project_id)
            action_id = a.id
            if not TestActionData.objects.filter(
                    action_id=action_id, test_id=test_id).exists():
                logger.debug("Adding action data: {}".format(url))
                df_url = df[(df.url == url)]
                url_data = pd.DataFrame()
                df_url_gr_by_ts = df_url.groupby(pd.TimeGrouper(freq='1Min'))
                url_data['avg'] = df_url_gr_by_ts.response_time.mean()
                url_data['median'] = df_url_gr_by_ts.response_time.median()
                url_data['count'] = df_url_gr_by_ts.success.count()
                df_url_gr_by_ts_only_errors = df_url[(
                    df_url.success == False
                )].groupby(pd.TimeGrouper(freq='1Min'))
                url_data[
                    'errors'] = df_url_gr_by_ts_only_errors.success.count()
                url_data['test_id'] = test_id
                url_data['url'] = url
                output_json = json.loads(
                    url_data.to_json(orient='index', date_format='iso'),
                    object_pairs_hook=OrderedDict)
                for row in output_json:
                    data = {
                        'timestamp': row,
                        'avg': output_json[row]['avg'],
                        'median': output_json[row]['median'],
                        'count': output_json[row]['count'],
                        'url': output_json[row]['url'],
                        'errors': output_json[row]['errors'],
                        'test_id': output_json[row]['test_id'],
                    }
                    test_action_data = TestActionData(
                        test_id=output_json[row]['test_id'],
                        action_id=action_id,
                        data=data)
                    test_action_data.save()

                url_agg_data = dict(
                    json.loads(df_url['response_time'].describe().to_json()))
                url_agg_data['99%'] = df_url['response_time'].quantile(.99)
                url_agg_data['90%'] = df_url['response_time'].quantile(.90)
                url_agg_data['weight'] = float(df_url['response_time'].sum())
                url_agg_data['errors'] = df_url[(
                    df_url['success'] == False)]['success'].count()
                test_action_aggregate_data = TestActionAggregateData(
                    test_id=test_id, action_id=action_id, data=url_agg_data)
                test_action_aggregate_data.save()

        # zip_results_file(jmeter_results_file)

        test_overall_data = pd.DataFrame()
        df_gr_by_ts = df.groupby(pd.TimeGrouper(freq='1Min'))
        test_overall_data['avg'] = df_gr_by_ts.response_time.mean()
        test_overall_data['median'] = df_gr_by_ts.response_time.median()
        test_overall_data['count'] = df_gr_by_ts.response_time.count()
        test_overall_data['test_id'] = test_id
        output_json = json.loads(
            test_overall_data.to_json(orient='index', date_format='iso'),
            object_pairs_hook=OrderedDict)
        for row in output_json:
            data = {
                'timestamp': row,
                'avg': output_json[row]['avg'],
                'median': output_json[row]['median'],
                'count': output_json[row]['count']
            }
            test_data = TestData(
                test_id=output_json[row]['test_id'], data=data)
            test_data.save()

    return render(request, "upload/success.html", {
        'result': 'ok',
        'test_name': test_name,
        'project_id': project_id,
        'num_lines': num_lines
    })


def configure_page(request, project_id):
    '''Generate HTML page to configure test`s attributes'''

    project = Project.objects.get(id=project_id)
    tests_list = Test.objects.filter(
        project_id=project_id).values().order_by('-start_time')
    return render(request, 'overall_configure_page.html',
                  {'tests_list': tests_list,
                   'project': project})


def projects_list(request):
    '''Return available projects list'''

    project_list = []
    projects_all = list(Project.objects.values())
    for project in projects_all:
        if project['show']:
            project_list.append(project)
    return JsonResponse(project_list, safe=False)


def get_project_tests_list(project_id):
    '''Return test`s list for some project'''

    t = Test.objects.filter(project__id=project_id).values().\
        order_by('-start_time')
    return t


def get_test_actions_list(test_id):
    '''Return actions list for some test'''

    t = TestActionData.objects.filter(
        test_id=test_id).distinct('action_id').values('action_id',
                                                      'action__url')
    return t


def tests_list(request, project_id):
    t = get_project_tests_list(project_id)
    return JsonResponse(list(t), safe=False)


def test_actions_list(request, test_id):
    t = get_test_actions_list(test_id)
    return JsonResponse(list(t), safe=False)


def composite_data(request):
    '''
    Return composite data for several actions 
    '''
    response = []
    arr = {}
    temp_data = []
    action_names = {"actions": []}
    if request.method == 'POST':
        test_ids = request.POST.getlist('test_ids[]')
        action_ids = request.POST.getlist('action_ids[]')
        for test_id in test_ids:
            if test_id != 0:
                for action_id in action_ids:
                    action_url = Action.objects.get(id=action_id).url
                    action_url = action_url.replace(" ", "_")
                    an = list(action_names["actions"])
                    col_name = action_url + "_avg_" + test_id
                    an.append(col_name)
                    action_names["actions"] = an
                    min_timestamp = TestActionData.objects. \
                        filter(test_id=test_id, action_id=action_id). \
                        values("test_id", "action_id"). \
                        aggregate(min_timestamp=Min(
                            RawSQL("((data->>%s)::timestamp)", ('timestamp',))))['min_timestamp']

                    mapping = {
                        col_name: RawSQL("((data->>%s)::numeric)", ('avg', ))
                    }
                    action_data = list(TestActionData.objects. \
                        filter(test_id=test_id, action_id=action_id). \
                        annotate(timestamp=(RawSQL("((data->>%s)::timestamp)", ('timestamp',)) - min_timestamp)). \
                        annotate(**mapping). \
                        values('timestamp', col_name). \
                        order_by('timestamp'))
                    data = json.loads(
                        json.dumps(
                            action_data, indent=4, sort_keys=True,
                            default=str))
                    for d in data:
                        timestamp = d['timestamp']
                        if timestamp not in arr:
                            arr[timestamp] = {col_name: d[col_name]}
                        else:
                            old_data = arr[timestamp]
                            old_data[col_name] = d[col_name]
                            arr[timestamp] = old_data
                    temp_data.append(arr)
        temp_data = temp_data[0]
        for timestamp in temp_data:
            v = temp_data[timestamp]
            v['timestamp'] = timestamp
            response.append(v)

        response.append(action_names)
    print response
    return JsonResponse(response, safe=False)


def get_test_for_project(project_id, n):
    '''
    Get first, second, N test for project with project_id
    '''
    t = list(Test.objects.filter(project__id=project_id)\
        .order_by('-start_time').values())[n]
    return t


def last_test(request, project_id):
    '''Return object for last executed test in project'''

    t = Test.objects.filter(project__id=project_id)\
        .order_by('-start_time').values()
    return JsonResponse([get_test_for_project(project_id, 0)], safe=False)


def project_history(request, project_id):
    '''
    Return whole list of tests with avg and median response times for project_id
    '''
    source = 'default'
    data = TestData.objects. \
        filter(test__project_id=project_id, test__show=True, source=source).\
        annotate(test_name=F('test__display_name')). \
        values('test_name'). \
        annotate(mean=Sum(RawSQL("((data->>%s)::numeric)", ('avg',))*RawSQL("((data->>%s)::numeric)", ('count',)))/Sum(RawSQL("((data->>%s)::numeric)", ('count',)))). \
        annotate(median=Sum(RawSQL("((data->>%s)::numeric)", ('median',))*RawSQL("((data->>%s)::numeric)", ('count',)))/Sum(RawSQL("((data->>%s)::numeric)", ('count',)))). \
        order_by('test__start_time')
    return JsonResponse(list(data), safe=False)


def test_info(request, project_id, build_number):
    '''Return test object by project_id and Jenkins build number'''

    t = Test.objects.filter(
        project__id=project_id, build_number=build_number).values()
    return JsonResponse(list(t), safe=False)


def test_info_from_id(request, test_id):
    '''Return test object by id'''

    t = Test.objects.filter(id=test_id).values()
    return JsonResponse(list(t), safe=False)


def prev_test_id(request, test_id):
    '''Return id of previous test for the current test with id'''

    p = Project.objects.\
        filter(test__id=test_id)
    start_time = Test.objects.filter(
        id=test_id).values('start_time')[0]['start_time']
    t = Test.objects.filter(start_time__lte=start_time, project=p).\
        values('id').order_by('-start_time')
    #data = db.get_prev_test_id(test_id, 2)
    return JsonResponse([list(t)[1]], safe=False)


def get_test_aggregate_table(test_id):
    '''Return aggregate data for the test'''

    aggregate_table = TestActionAggregateData.objects.annotate(url=F('action__url')).filter(test_id=test_id). \
        values('url',
               'action_id',
               'data')
    return aggregate_table


def test_report(request, test_id):
    '''Generate HTML page with report for the test'''

    test_description = Test.objects.filter(id=test_id).values()
    aggregate_table = get_test_aggregate_table(test_id)
    return render(request, 'report.html', {
        'test_description': test_description[0],
        'aggregate_table': aggregate_table
    })


def composite(request, project_id):
    '''Generate html page with conposite graph'''

    tests_list = Test.objects.filter(project__id=project_id).values().\
        order_by('-start_time')
    return render(request, 'composite.html', {'tests_list': tests_list})


def action_report(request, test_id, action_id):
    '''
    Generate HTML page with detail data about some action
    which were execute during the test
    '''

    action_aggregate_data = list(
        TestActionAggregateData.objects.annotate(test_name=F(
            'test__display_name')).filter(
                action_id=action_id, test_id__lte=test_id).values(
                    'test_name', 'data').order_by('-test__start_time'))[:5]
    action_data = []
    for e in action_aggregate_data:
        data = e['data']
        mean = data['mean']
        min = data['min']
        max = data['max']
        q3 = data['75%']
        q2 = data['50%']
        std = data['std']
        if '25%' in data:
            q1 = data['25%']
        else:
            # WTF lol
            q1 = q2 - (q3 - q2)
        IQR = q3 - q1
        LW = q1 - 1.5 * IQR
        if LW < 0:
            LW = 0.1
        UW = q3 + 1.5 * IQR
        test_name = e['test_name']
        action_data.append({
            "q1": q1,
            "q2": q2,
            "q3": q3,
            "IQR": IQR,
            "LW": LW,
            "UW": UW,
            "mean": mean,
            "min": min,
            "max": max,
            "std": std,
            "test_name": test_name
        })
    test_start_time = TestActionData.objects. \
        filter(test_id=test_id). \
        aggregate(min_timestamp=Min(
            RawSQL("((data->>%s)::timestamp)", ('timestamp',))))['min_timestamp']
    test_errors = TestError.objects.annotate(
        text=F('error__text'), code=F('error__code')).filter(
            test_id=test_id, action_id=action_id).values(
                'text', 'code', 'count')
    return render(
        request,
        'action_report.html', {
            'test_id': test_id,
            'action': Action.objects.get(id=action_id),
            'action_data': action_data,
            'test_start_time': test_start_time,
            'test_errors': test_errors,
        })


def action_rtot(request, test_id, action_id):
    '''Return response times over time data for the action'''
    min_timestamp = TestActionData.objects. \
        filter(test_id=test_id, action_id=action_id). \
        values("test_id", "action_id"). \
        aggregate(min_timestamp=Min(
            RawSQL("((data->>%s)::timestamp)", ('timestamp',))))['min_timestamp']
    x = TestActionData.objects. \
        filter(test_id=test_id, action_id=action_id). \
        annotate(timestamp=(RawSQL("((data->>%s)::timestamp)", ('timestamp',)) - min_timestamp)). \
        annotate(average=RawSQL("((data->>%s)::numeric)", ('avg',))). \
        annotate(median=RawSQL("((data->>%s)::numeric)", ('median',))). \
        annotate(rps=(RawSQL("((data->>%s)::numeric)", ('count',))) / 60). \
        annotate(errors=(RawSQL("((data->>%s)::numeric)", ('errors',))) / 60). \
        values('timestamp', "average", "median", "rps", "errors"). \
        order_by('timestamp')
    data = json.loads(
        json.dumps(list(x), indent=4, sort_keys=True, default=str))
    return JsonResponse(data, safe=False)


def available_test_monitoring_metrics(request, source, test_id, server_id):
    '''Return list of metrics which are available for the test and server'''
    x = ServerMonitoringData.objects.\
        filter(test_id=test_id, server_id=server_id, source=source).values('data')[:1]
    data = list(x)[0]["data"]
    metrics = []
    for value in data:
        if "test_id" not in value and "timestamp" not in value:
            metrics.append({"metric": value})
    metrics.append({"metric": "CPU_all"})
    return JsonResponse(metrics, safe=False)


def test_servers(request, source, test_id):
    '''Return server list for the test'''

    servers_list = Server.objects.\
        filter(servermonitoringdata__test_id=test_id, servermonitoringdata__source=source).\
        values().distinct()

    return JsonResponse(list(servers_list), safe=False)


def test_change(request, test_id):
    '''Change test data'''

    test = Test.objects.get(id=test_id)
    response = []
    if request.method == 'POST':
        if 'show' in request.POST:
            show = request.POST.get('show', '')
            test.show = True if show == 'true' else False
            test.save()
        elif 'display_name' in request.POST:
            display_name = request.POST.get('display_name', '')
            test.display_name = display_name
            test.save()
        response = [{"message": "Test data was changed"}]
    return JsonResponse(response, safe=False)


def get_compare_tests_server_monitoring_data(test_id,
                                             num_of_tests,
                                             order='-test__start_time'):
    '''Return cpu load data for N tests before the current one'''

    project = Test.objects.filter(id=test_id).values('project_id')
    project_id = project[0]['project_id']
    start_time = Test.objects.filter(
        id=test_id).values('start_time')[0]['start_time']
    data = (ServerMonitoringData.objects.filter(
        test__start_time__lte=start_time,
        test__project_id=project_id,
        test__show=True).values(
            'test__display_name', 'server__server_name', 'test__start_time'
        ).annotate(cpu_load=RawSQL(
            "((data->>%s)::float)+((data->>%s)::float)+((data->>%s)::float)", (
                'CPU_user',
                'CPU_iowait',
                'CPU_system', ))).annotate(
                    cpu_load=Avg('cpu_load')).order_by('-test__start_time'))
    return data


def compare_tests_cpu(request, test_id, num_of_tests):
    '''Compare CPU load between current and N previous tests'''
    data = get_compare_tests_server_monitoring_data(test_id, num_of_tests)
    # FUCK YOU DJANGO ORM >_<. DENSE_RANK does not work so:
    current_rank = 1
    counter = 0
    arr = []
    for d in data:
        if counter < 1:
            d['rank'] = current_rank
        else:
            if int(d['test__start_time']) == int(
                    data[counter - 1]['test__start_time']):
                d['rank'] = current_rank
            else:
                current_rank += 1
                d['rank'] = current_rank
        # filter by rank >_<
        if int(d['rank']) <= int(num_of_tests) + 1:
            # C3.js does not accept "."
            d['server__server_name'] = d['server__server_name'].\
                replace(".", "_")
            arr.append(d)
        counter += 1
    response = list(arr)
    response = to_pivot(response, 'test__display_name', 'server__server_name',
                        'cpu_load')
    response = response.to_json(orient='index')
    # return HttpResponse(response)
    return HttpResponse(
        json.loads(
            json.dumps(response, sort_keys=False),
            object_pairs_hook=OrderedDict))


def get_compare_tests_aggregate_data(test_id,
                                     num_of_tests,
                                     order='-test__start_time',
                                     source='default'):
    '''
    Compares given test with test_id against num_of_tests previous
    '''
    project = Test.objects.filter(id=test_id).values('project_id')
    start_time = Test.objects.filter(
        id=test_id).values('start_time')[0]['start_time']
    project_id = project[0]['project_id']
    if source == 'default':
        data = TestData.objects. \
                filter(test__start_time__lte=start_time, test__project_id=project_id, test__show=True, source=source).\
                annotate(display_name=F('test__display_name')). \
                annotate(start_time=F('test__start_time')). \
                values('display_name', 'start_time'). \
                annotate(average=Sum(RawSQL("((data->>%s)::numeric)", ('avg',))*RawSQL("((data->>%s)::numeric)", ('count',)))/Sum(RawSQL("((data->>%s)::numeric)", ('count',)))). \
                annotate(median=Sum(RawSQL("((data->>%s)::numeric)", ('median',))*RawSQL("((data->>%s)::numeric)", ('count',)))/Sum(RawSQL("((data->>%s)::numeric)", ('count',)))). \
                order_by(order)[:num_of_tests]
    elif source == 'graphite':
        tests = Test.objects.filter(
            start_time__lte=start_time, project_id=project_id,
            show=True).values().order_by('-start_time')[:num_of_tests]
        print tests
        for t in tests:
            test_id = t['id']
            if not ServerMonitoringData.objects.filter(
                    test_id=test_id,
                    source='graphite').exists() or not TestData.objects.filter(
                        test_id=test_id, source='graphite').exists():
                result = update_test_graphite_data(test_id)
        data = TestData.objects. \
                filter(test__start_time__lte=start_time, test__project_id=project_id, test__show=True, source=source).\
                annotate(display_name=F('test__display_name')). \
                annotate(start_time=F('test__start_time')). \
                values('display_name', 'start_time'). \
                annotate(average=Avg(RawSQL("((data->>%s)::numeric)", ('avg',)))). \
                annotate(median=Avg(RawSQL("((data->>%s)::numeric)", ('median',)))). \
                order_by(order).order_by(order)[:num_of_tests]
    return data


def compare_tests_avg(request, test_id):
    '''Compare average response times for current and N previous tests'''
    if request.method == 'POST':
        source = request.POST.get('source', '0')
        num_of_tests = request.POST.get('num_of_tests_to_compare', '0')
        data = get_compare_tests_aggregate_data(
            test_id, num_of_tests, source=source)
        current_rank = 1
        counter = 0
        arr = []
        for d in data:
            if counter < 1:
                d['rank'] = current_rank
            else:
                if int(d['start_time']) == int(
                        data[counter - 1]['start_time']):
                    d['rank'] = current_rank
                else:
                    current_rank += 1
                    d['rank'] = current_rank
            # filter by rank >_<
            if int(d['rank']) <= int(num_of_tests) + 1:
                arr.append(d)
            counter += 1
        response = list(arr)
    return JsonResponse(response, safe=False)


def test_rtot_data(request, test_id):
    '''Return response tines over tine data for the test'''

    data = []
    if request.method == 'POST':
        source = request.POST.get('source', '0')
        min_timestamp = TestData.objects. \
            filter(test_id=test_id, source=source). \
            values("test_id").\
            aggregate(min_timestamp=Min(
                RawSQL("((data->>%s)::timestamp)", ('timestamp',))))['min_timestamp']
        x = TestData.objects. \
            filter(test_id=test_id, source=source). \
            annotate(timestamp=(RawSQL("((data->>%s)::timestamp)", ('timestamp',)) - min_timestamp)). \
            annotate(average=RawSQL("((data->>%s)::numeric)", ('avg',))). \
            annotate(median=RawSQL("((data->>%s)::numeric)", ('median',))). \
            annotate(rps=(RawSQL("((data->>%s)::numeric)", ('count',))) / 60). \
            values('timestamp', "average", "median", "rps"). \
            order_by('timestamp')
        data = json.loads(
            json.dumps(list(x), indent=4, sort_keys=True, default=str))
        return JsonResponse(data, safe=False)


def test_errors(request, test_id):
    '''
    Return overall success/errors percentage 
    '''

    data = TestActionAggregateData.objects.filter(test_id=test_id). \
            annotate(errors=RawSQL("((data->>%s)::numeric)", ('errors',))). \
            annotate(count=RawSQL("((data->>%s)::numeric)", ('count',))). \
            aggregate(count_sum=Sum(F('count'), output_field=FloatField()),
             errors_sum=Sum(F('errors'), output_field=FloatField()))
    errors_percentage = data['errors_sum'] * 100 / data['count_sum']
    response = [{
        "fail_%": errors_percentage,
        "success_%": 100 - errors_percentage
    }]
    return JsonResponse(response, safe=False)


def test_top_avg(request, test_id, top_number):
    '''
    Return top N actions with highest average response times
    '''

    data = TestActionAggregateData.objects.filter(test_id=test_id). \
            annotate(url=F('action__url')). \
            annotate(average=RawSQL("((data->>%s)::numeric)", ('mean',))). \
            order_by('-average').values('url', 'average')[:top_number]
    return JsonResponse(list(data), safe=False)


def test_top_errors(request, test_id):
    '''
    Return top N actions with highest errors percentage
    '''

    data = TestActionAggregateData.objects.filter(test_id=test_id). \
        annotate(url=F('action__url')). \
        annotate(errors=Round(RawSQL("((data->>%s)::numeric)", ('errors',))*100/RawSQL("((data->>%s)::numeric)", ('count',)))). \
        order_by('-errors').values('url', 'action_id', 'errors')[:5]
    return JsonResponse(list(data), safe=False)


def metric_max_value(request, test_id, server_id, metric):
    '''Return maximum value for some metric'''

    max_value = {}
    if 'CPU' in metric:
        max_value = {'max_value': 100}
    else:
        max_value = ServerMonitoringData.objects. \
            filter(test_id=test_id, server_id=server_id).\
            annotate(val=RawSQL("((data->>%s)::numeric)", (metric,))).\
            aggregate(max_value=Max('val', output_field=FloatField()))
    return JsonResponse(max_value, safe=False)


def tests_compare_aggregate_new(request, test_id_1, test_id_2):
    '''Return comparasion data for all actions in two tests'''
    response = []
    action_data_1 = TestActionAggregateData.objects.annotate(
        action_name=F('action__url')).annotate(mean=RawSQL(
            "((data->>%s)::numeric)",
            ('mean', ))).filter(test_id=test_id_1).values(
                'action_id', 'action_name', 'mean')
    for action in action_data_1:
        action_id = action['action_id']
        if TestActionAggregateData.objects.filter(
                action_id=action_id, test_id=test_id_2).exists():
            action_data_2 = TestActionAggregateData.objects.annotate(
                action_name=F('action__url')).annotate(mean=RawSQL(
                    "((data->>%s)::numeric)", ('mean', ))).filter(
                        action_id=action_id, test_id=test_id_2).values(
                            'action_name', 'mean')[0]
            mean_1 = action['mean']
            mean_2 = action_data_2['mean']
            mean_diff_percent = (mean_1 - mean_2) / mean_2 * 100
        else:
            mean_diff_percent = 0
        response.append({
            'action_name': action['action_name'],
            'mean_diff_percent': mean_diff_percent
        })
    return JsonResponse(response, safe=False)


def check_graphite_data(request, test_id):
    if not ServerMonitoringData.objects.filter(
            test_id=test_id,
            source='graphite').exists() or not TestData.objects.filter(
                test_id=test_id, source='graphite').exists():
        result = update_test_graphite_data(test_id)
        response = {
            "message": {
                "text": "Graphite data was updated",
                "type": "success",
                "msg_params": {
                    "result": result
                }
            }
        }
    else:
        response = {
            "message": {
                "text": "Graphite data is already exists",
                "type": "success",
                "msg_params": {}
            }
        }
    return JsonResponse(response, safe=False)


def server_monitoring_data(request, test_id):
    '''Return monitoring data for some test and server'''
    data = []
    if request.method == 'POST':
        server_id = request.POST.get('server_id', '0')
        metric = request.POST.get('metric', '0')
        source = request.POST.get('source', '0')

        min_timestamp = ServerMonitoringData.objects. \
            filter(test_id=test_id, server_id=server_id, source=source). \
            values("test_id"). \
            aggregate(min_timestamp=Min(
                RawSQL("((data->>%s)::timestamp)", ('timestamp',))))['min_timestamp']

        if metric == 'CPU_all':
            metric_mapping = {
                metric:
                RawSQL(
                    "(((data->>%s)::numeric)+((data->>%s)::numeric)+((data->>%s)::numeric))",
                    (
                        'CPU_iowait',
                        'CPU_user',
                        'CPU_system', ))
            }
        else:
            metric_mapping = {
                metric: RawSQL("((data->>%s)::numeric)", (metric, ))
            }
        x = ServerMonitoringData.objects. \
            filter(test_id=test_id, server_id=server_id, source=source). \
            annotate(timestamp=RawSQL("((data->>%s)::timestamp)", ('timestamp',)) - min_timestamp).\
            annotate(**metric_mapping). \
            values('timestamp', metric)
        #annotate(metric=RawSQL("((data->>%s)::numeric)", (metric,)))
        data = json.loads(
            json.dumps(list(x), indent=4, sort_keys=True, default=str))
    return JsonResponse(data, safe=False)


def tests_compare_report(request, test_id_1, test_id_2):
    '''
    Compare current test (test_id_1) with one of the previous
    '''
    report = {
        'absense': [],
        'higher_response_times': [],
        'lower_response_times': [],
        'lower_count': [],
        'new_action_in_test': [],
        'cpu_steal': [],
    }
    sp = int(
        Configuration.objects.get(name='signifficant_actions_compare_percent')
        .value)
    if not ServerMonitoringData.objects.filter(
            test_id=test_id_1, source='graphite').exists():
        result = update_test_graphite_data(test_id_1)
    if not ServerMonitoringData.objects.filter(
            test_id=test_id_2, source='graphite').exists():
        result = update_test_graphite_data(test_id_2)

    cpu_steal_data = ServerMonitoringData.objects.filter(
        test_id__in=[test_id_1, test_id_2], source='graphite').annotate(
            server_name=F('server__server_name'),
            test_name=F('test__display_name')).values(
                'server_name', 'test_name').annotate(cpu_steal=Avg(
                    RawSQL("((data->>%s)::float)", ('CPU_steal', ))))

    for d in cpu_steal_data:
        if d['cpu_steal'] > 0:  # ??
            report['cpu_steal'].append({
                'server_name': d['server_name'],
                'test_name': d['test_name'],
                'cpu_steal': d['cpu_steal'],
                "severity": "danger",
            })

    test_1_actions = list(
        TestActionAggregateData.objects.annotate(url=F('action__url'))
        .filter(test_id=test_id_1).values('action_id', 'url', 'data'))
    test_2_actions = list(
        TestActionAggregateData.objects.annotate(url=F('action__url'))
        .filter(test_id=test_id_2).values('action_id', 'url', 'data'))

    for action in test_1_actions:
        # Check for new actions executed during the last test
        action_id = action['action_id']
        action_url = action['url']
        if not TestActionAggregateData.objects.filter(
                test_id=test_id_2, action_id=action_id).exists(
                ) and TestActionAggregateData.objects.filter(
                    test_id=test_id_1, action_id=action_id).exists():
            report['new_action_in_test'].append({
                "action": action_url,
                "severity": "danger",
            })

    for action in test_2_actions:
        action_id = action['action_id']
        action_url = action['url']
        action_data_2 = action['data']

        # Check if one of the actions were not executed
        if not TestActionAggregateData.objects.filter(
                test_id=test_id_1, action_id=action_id).exists():
            report['absense'].append({
                "action": action_url,
                "severity": "danger",
            })
        else:
            action_data_1 = list(
                TestActionAggregateData.objects.filter(
                    test_id=test_id_1, action_id=action_id).values('data'))[0][
                        'data']
            # Student t-criteria
            Xa = action_data_1['mean']
            Xb = action_data_2['mean']
            Sa = 0 if action_data_1['std'] is None else action_data_1['std']
            Sb = 0 if action_data_2['std'] is None else action_data_2['std']
            Na = action_data_1['count']
            Nb = action_data_2['count']
            # df = Na - 1 + Nb - 1
            # Satterthwaite Formula for Degrees of Freedom
            if Xa > 10 and Xb > 10 and not Sa == 0 and not Sb == 0:
                df = math.pow(
                    math.pow(Sa, 2) / Na + math.pow(Sb, 2) / Nb, 2) / (
                        math.pow(math.pow(Sa, 2) / Na, 2) /
                        (Na - 1) + math.pow(math.pow(Sb, 2) / Nb, 2) /
                        (Nb - 1))
                if df > 0:
                    t = stats.t.ppf(1 - 0.01, df)
                    logger.debug(
                        'Action: {0} t: {1} Xa: {2} Xb: {3} Sa: {4} Sb: {5} Na: {6} Nb: {7} df: {8}'.
                        format(action_url,
                               stats.t.ppf(1 - 0.025, df), Xa, Xb, Sa, Sb, Na,
                               Nb, df))
                    Sab = math.sqrt(((Na - 1) * math.pow(Sa, 2) +
                                     (Nb - 1) * math.pow(Sb, 2)) / df)
                    Texp = (math.fabs(Xa - Xb)) / (
                        Sab * math.sqrt(1 / Na + 1 / Nb))
                    logger.debug('Action: {0} Texp: {1} Sab: {2}'.format(
                        action_url, Texp, Sab))

                    if Texp > t:
                        diff_percent = abs(100 - 100 * Xa / Xb)
                        if Xa > Xb:
                            if diff_percent > sp:
                                if diff_percent > 10:
                                    severity = "danger"
                                else:
                                    severity = "warning"
                                report["higher_response_times"].append({
                                    "action":
                                    action_url,
                                    "severity":
                                    severity,
                                    "action_data_1":
                                    action_data_1,
                                    "action_data_2":
                                    action_data_2,
                                })
                        else:
                            if diff_percent > sp:
                                report["lower_response_times"].append({
                                    "action":
                                    action_url,
                                    "severity":
                                    "success",
                                    "action_data_1":
                                    action_data_1,
                                    "action_data_2":
                                    action_data_2,
                                })

                        if Na / 100 * Nb < 90:
                            report["lower_count"].append({
                                "action":
                                action_url,
                                "severity":
                                "warning",
                                "action_data_1":
                                action_data_1,
                                "action_data_2":
                                action_data_2,
                            })
    return render(
        request,
        'compare_report.html', {
            'report': report,
            'test_1': Test.objects.get(id=test_id_1),
            'test_2': Test.objects.get(id=test_id_2),
        })
    #return JsonResponse(report, safe=False)


def action_graphs(request, test_id):
    actions_list = list(
        TestActionAggregateData.objects.annotate(name=F('action__url')).filter(
            test_id=test_id).values('action_id', 'name'))
    return render(request, 'action_graphs.html',
                  {'actions_list': actions_list,
                   'test_id': test_id})


def dashboard_compare_tests_list(tests_list):
    '''Return comparasion data for dashboard'''
    tests = []
    for t in tests_list:
        test_id = t['id']
        project_id = t['project_id']

        project_tests = Test.objects.filter(
            project_id=project_id, id__lte=test_id).order_by('-start_time')

        if project_tests.count() > 1:
            prev_test_id = project_tests[1].id
        else:
            prev_test_id = test_id
        test_data = TestActionAggregateData.objects.filter(test_id=test_id). \
        annotate(errors=RawSQL("((data->>%s)::numeric)", ('errors',))). \
        annotate(count=RawSQL("((data->>%s)::numeric)", ('count',))). \
        annotate(weight=RawSQL("((data->>%s)::numeric)", ('weight',))). \
        aggregate(
            count_sum=Sum(F('count'), output_field=FloatField()),
            errors_sum=Sum(F('errors'), output_field=FloatField()),
            overall_avg = Sum(F('weight'))/Sum(F('count'))
            )

        prev_test_data = TestActionAggregateData.objects.filter(test_id=prev_test_id). \
        annotate(errors=RawSQL("((data->>%s)::numeric)", ('errors',))). \
        annotate(count=RawSQL("((data->>%s)::numeric)", ('count',))). \
        annotate(weight=RawSQL("((data->>%s)::numeric)", ('weight',))). \
        aggregate(
            count_sum=Sum(F('count'), output_field=FloatField()),
            errors_sum=Sum(F('errors'), output_field=FloatField()),
            overall_avg = Sum(F('weight'))/Sum(F('count'))
            )
        try:
            errors_percentage = test_data['errors_sum'] * 100 / test_data[
                'count_sum']
        except TypeError, ZeroDivisionError:
            errors_percentage = 0
        success_requests = 100 - errors_percentage
        # TODO: improve this part
        if success_requests >= 98:
            result = 'success'
        elif success_requests < 98 and success_requests >= 95:
            result = 'warning'
        else:
            result = 'danger'
        tests.append({
            'project_name':
            t['project__project_name'],
            'display_name':
            t['display_name'],
            'parameters':
            t['parameters'],
            'start_time':
            t['start_time'],
            'success_requests':
            success_requests,
            'test_avg_response_times':
            test_data['overall_avg'],
            'prev_test_avg_response_times':
            prev_test_data['overall_avg'],
            'result':
            result,
        })
    return tests


def dashboard(request):
    '''
    Generate dashboard page
    '''
    last_tests_by_project = []
    projects_list = []
    s = Test.objects.values('project_id').annotate(
        latest_time=Max('start_time'))
    for i in s:
        project_id = i['project_id']
        # Only tests executed in last 30 days
        if int(i['latest_time']) >= int(
                time.time() * 1000) - 1000 * 1 * 60 * 60 * 24 * 30:
            r = Test.objects.filter(project_id=project_id, start_time=i['latest_time']).\
                values('project__project_name', 'display_name', 'id','project_id','parameters', 'start_time')
            last_tests_by_project.append(list(r)[0])
            projects_list.append(Project.objects.get(id=project_id))

    last_tests = Test.objects.filter(project__show=True).values(
        'project__project_name', 'project_id', 'display_name', 'id',
        'parameters', 'start_time').order_by('-start_time')[:10]
    tests = dashboard_compare_tests_list(last_tests)
    tests_by_project = dashboard_compare_tests_list(last_tests_by_project)
    logger.debug(projects_list)
    return render(request, 'dashboard.html', {
        'last_tests': tests,
        'last_tests_by_project': tests_by_project,
        'projects_list': projects_list
    })


class Analyze(TemplateView):
    def get(self, request, **kwargs):
        return render(request, 'analyze.html', context=None)


class History(TemplateView):
    def get(self, request, **kwargs):
        return render(request, 'history.html', context=None)


def confluence_test_report(test_id):
    content = ""
    aggregate_table = get_test_aggregate_table(test_id)
    aggregate_table_html = render_to_string(
        'confluence/aggregate_table.html',
        {'aggregate_table': aggregate_table})
    content += "<h2>Aggregate table</h2>"
    content += aggregate_table_html
    return content


def confluence_project_report(project_id):
    project = Project.objects.get(id=project_id)
    content = """
    <h2>Load testing report for: {0}</h2>
    <hr/>    
    {1}  
    <hr/> 
    """
    last_test = get_test_for_project(project_id, 0)
    data = get_compare_tests_aggregate_data(
        last_test['id'], 10, order='start_time')
    agg_response_times_graph = generate_confluence_graph(project, list(data))
    #data = get_compare_tests_server_monitoring_data(last_test['id'], 10, order='start_time')
    #agg_cpu_util_graph = generate_confluence_graph(project, list(data))

    last_tests = Test.objects.filter(project_id=project_id).values(
        'project__project_name', 'project_id', 'display_name', 'id',
        'parameters', 'start_time').order_by('-start_time')[:10]
    tests = dashboard_compare_tests_list(last_tests)
    last_tests_table_html = render_to_string(
        'confluence/last_tests_table.html', {'last_tests': tests})

    content = content.format(project.project_name, agg_response_times_graph)
    content += last_tests_table_html
    return content


def generate_confluence_project_report(request, project_id):
    project = Project.objects.get(id=project_id)
    error = ""
    successful = True
    wiki_url = Configuration.objects.get(name='wiki_url').value
    wiki_user = Configuration.objects.get(name='wiki_user').value
    wiki_password = Configuration.objects.get(name='wiki_password').value
    cp = confluenceposter.ConfluencePoster(wiki_url, wiki_user, wiki_password)
    cp.login()

    space = project.confluence_space

    target_page = '{0} Load Testing Reports'.format(project.project_name)

    target_url = '{}/display/{}/{}'.format(wiki_url, space, target_page)

    # Post parent summary page
    try:
        logger.info('Try to open Confluence page: ' + target_page)
        page_parent = cp.get_page(space, target_page)
    except Exception as e:
        error = e
        logger.error(e)
        successful = False

    page_parent['content'] = confluence_project_report(project_id)
    try:
        cp.post_page(page_parent)
    except Exception as e:
        error = e
        logger.error(e)
        successful = False

    page_parent_id = page_parent['id']
    del page_parent['id']
    del page_parent['url']
    del page_parent['modified']
    del page_parent['created']
    del page_parent['version']
    del page_parent['contentStatus']
    # Post reports for all tests
    for test in Test.objects.filter(project_id=project_id).values():
        test_id = test['id']
        test_name = test['display_name']
        test_report_page_exists = True
        try:
            page_test_report = cp.get_page(space, test_name)
        except Exception as e:
            test_report_page_exists = False
            page_test_report = page_parent
            page_test_report['parentId'] = page_parent_id
            page_test_report['title'] = test_name
        if not test_report_page_exists:
            logger.info('Creating test report page: {}'.format(test_name))
            page_test_report['content'] = confluence_test_report(test_id)
            try:
                cp.post_page(page_test_report)
            except Exception as e:
                error = e
                logger.error(e)
                successful = False

    cp.logout()
    if successful:
        response = {
            "message": {
                "text":
                "Project report is posted to Confluence: {}".format(
                    target_url),
                "type":
                "success",
                "msg_params": {
                    "link": target_url
                }
            }
        }
    else:
        response = {
            "message": {
                "text": str(e),
                "type": "danger",
                "msg_params": {
                    "link": target_url
                }
            }
        }

    return JsonResponse(response, safe=False)


def queryset_to_json(set):
    return json.loads(
        json.dumps(list(set), indent=4, sort_keys=True, default=str))
