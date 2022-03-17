# -*- coding: utf-8 -*-
import json
import logging
import math
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
import pandas as pd
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Avg, FloatField, Func, Max, Min, Sum
from django.db.models.expressions import F, RawSQL
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.generic import TemplateView
from pylab import *
from scipy import stats
from django.views.decorators.http import require_POST
from ltc.base.utils.confluence import confluenceposter
from ltc.base.utils.confluence.helpers import generate_confluence_graph
from ltc.analyzer.models import (
    Action, Server, ServerMonitoringData,
    TestActionAggregateData, TestActionData,
    TestData, TestDataResolution, TestError
)
from ltc.base.models import (
    Project,
    Test,
    Configuration,
)
from ltc.controller.views import *

logger = logging.getLogger('django')

dateconv = np.vectorize(datetime.datetime.fromtimestamp)


@login_required
def index(request):
    context = {}
    context['projects'] = Project.objects.distinct()
    if request.method == 'GET':
        project_id = request.GET.get('project_id', '')
        test_id = request.GET.get('test_id', '')
        if project_id:
            context['project_'] = Project.objects.get(id=project_id)
            context['tests'] = Test.objects.filter(
                project_id=project_id
            ).order_by(F('started_at').desc(nulls_last=True))
        if test_id:
            test = Test.objects.get(id=test_id)
            project = test.project
            context['tests'] = Test.objects.filter(
                project=project
            ).order_by(F('started_at').desc(nulls_last=True))
            context['test_'] = test
            context['project_'] = project
    return render(request, 'analyzer/index.html', context)



@require_POST
def test_data(request):
    response = {}
    test_id = request.POST.get('test_id', '')
    response['test_id'] = test_id
    data = Test.objects.filter(id=test_id).prefetch_related(
        'testdata_set',
        'testactionaggregatedata_set',
        'testactiondata_set',
        'servermonitoringdata_set'
    )
    data = data.first()
    response['name'] = data.name
    test_action_aggregate_data = []
    for d in data.testactionaggregatedata_set.all():
        d_ = d.data
        d_['action'] = d.action.name
        test_action_aggregate_data.append(d_)
    test_data = []
    for d in data.testdata_set.all():
        d_ = d.data
        test_data.append(d_)

    server_monitoring_data = {}
    for d in data.servermonitoringdata_set.all():
        d_ = d.data
        server_monitoring_data.setdefault(
            d.server.server_name.replace(".", "_"), []
        ).append(d_)

    prev_tests = Test.objects.filter(
        started_at__lte=data.started_at,
        project=data.project,
    ).order_by(F('started_at').desc(nulls_last=True))[:15]
    compare_data = []
    for t in prev_tests:
        if not t.get_test_metric('mean'):
            continue
        test_name = t.name
        if not test_name:
            test_name = f'{t.project.name} - {t.id}'
        compare_data.append(
            {
                'test_name': test_name,
                'mean': t.get_test_metric('mean')[0]['mean'],
                'median': t.get_test_metric('median')[0]['median'],
                'cpu_load': t.get_test_metric('cpu_load')
            }
        )
    response['test_action_aggregate_data'] = test_action_aggregate_data
    response['test_data'] = test_data
    response['server_monitoring_data'] = server_monitoring_data
    response['compare_data'] = compare_data
    return JsonResponse(response)


def compare_table(tests):
    '''Return comparasion data for all actions in two tests'''
    compare_table = []
    if len(tests) < 0:
        return
    action_data_1 = TestActionAggregateData.objects.annotate(
        name=F('action__name')
    ).filter(test_id=tests[0].id).values(
        'action_id',
        'name',
        'data',
    )
    for action in action_data_1:
        action_id = action['action_id']
        if TestActionAggregateData.objects.filter(
            action_id=action_id, test_id=tests[1].id
        ).exists():
            action_data_2 = TestActionAggregateData.objects.annotate(
                name=F('action__name')
            ).filter(
                action_id=action_id, test_id=tests[1].id
            ).values('action_id', 'name', 'data')[0]
            compare_table.append({
                'name': action['name'],
                'mean_1': action['data']['mean'],
                'mean_2': action_data_2['data']['mean'],
                'p50_1': action['data']['50%'],
                'p50_2': action_data_2['data']['50%'],
                'p90_1': action['data']['90%'],
                'p90_2': action_data_2['data']['90%'],
                'count_1': action['data']['count'],
                'count_2': action_data_2['data']['count'],
                'max_1': action['data']['max'],
                'max_2': action_data_2['data']['max'],
                'min_1': action['data']['min'],
                'min_2': action_data_2['data']['min'],
                'errors_1': action['data']['errors'],
                'errors_2': action_data_2['data']['errors'],
            })
    return compare_table


@require_POST
def compare_highlights(request):
    """
    Show comparasion highlights for the test.

    **Template:**

    :template:`test_report/compare_highlights.html`
    """
    tests = []
    test_ids = request.POST.getlist('test_ids[]')
    if len(test_ids) >= 1:
        test = Test.objects.get(id=test_ids[0])
        tests.append(test)
    if len(test_ids) < 2:
        tests.append(test.prev_test())
    elif len(test_ids) == 2:
        if int(test_ids[1]) > 0:
            tests.append(Test.objects.get(id=test_ids[1]))
        else:
            tests.append(test.prev_test())
    highlights = {}
    highlights['critical'] = []
    highlights['warning'] = []
    highlights['success'] = []
    actions = {}
    actions_data = {}
    for test in tests:
        actions[
            test.id
        ] = TestActionAggregateData.objects.annotate(
            name=F('action__name')
        ).filter(test=test).values('name', 'action_id')
        actions_data[
            test.id
        ] = TestActionAggregateData.objects.annotate(
            name=F('action__name')
        ).filter(test=test).values('name', 'data')
    highlights['warning'] = [
        {'action': action, 'type': 'new_actions'}
        for action in actions[tests[0].id]
        if action not in actions[tests[1].id]
    ]

    highlights['warning'] = [
        {'action': action, 'type': 'absent_actions'}
        for action in actions[tests[1].id]
        if action not in actions[tests[0].id]
    ]

    sp, _ = Configuration.objects.get_or_create(
        name='signifficant_actions_compare_percent',
        defaults={
            'value': '10',
            'description': 'Signifficant actions compare percent',
        }
    )

    sp = int(sp.value)
    for a in actions_data[tests[1].id]:
        action = {}
        action['other_test'] = a
        action_name = action['other_test']['name']
        a_ = actions_data[
            tests[0].id
        ].filter(name=action_name)
        if a_.first() is None:
            continue
        action['current_test'] = a_.first()

        # Student t-criteria
        Xa = action['current_test']['data']['mean']
        Xb = action['other_test']['data']['mean']
        Sa = (
            0 if action['current_test']['data']['std'] is None
            else action['current_test']['data']['std']
        )
        Sb = (
            0 if action['other_test']['data']['std'] is None
            else action['other_test']['data']['std']
        )
        Na = action['current_test']['data']['count']
        Nb = action['other_test']['data']['count']
        # df = Na - 1 + Nb - 1
        # Satterthwaite Formula for Degrees of Freedom
        if Xa > 10 and Xb > 10 and not Sa == 0 and not Sb == 0:
            df = math.pow(
                    math.pow(Sa, 2) / Na + math.pow(Sb, 2) / Nb, 2) / (
                    math.pow(math.pow(Sa, 2) / Na, 2) /
                    (Na - 1) + math.pow(math.pow(Sb, 2) / Nb, 2) /
                    (Nb - 1)
                )
            if df > 0:
                t = stats.t.ppf(1 - 0.01, df)
                Sab = math.sqrt(
                    ((Na - 1) * math.pow(Sa, 2) + (Nb - 1) * math.pow(Sb, 2))
                    / df
                )
                Texp = (math.fabs(Xa - Xb)) / (
                        Sab * math.sqrt(1 / Na + 1 / Nb))
                if Texp > t:
                    diff_percent = abs(100 - 100 * Xa / Xb)
                    if Xa > Xb:
                        if diff_percent > sp:
                            highlights['critical'].append({
                                'action': action,
                                'type': 'higher_response_times',
                            })
                    else:
                        if diff_percent > sp:
                            highlights['success'].append({
                                'action': action,
                                'type': 'lower_response_times',
                            })
                    if Na / 100 * Nb < 90:
                        highlights['warning'].append({
                            'action': action,
                            'type': 'lower_count',
                        })
    return render(
        request,
        'analyzer/report/test_report/highlights.html', {
            'highlights': highlights,
            'tests': tests,
            'compare_table': compare_table(tests)
        }
    )


def action_details(request, test_id, action_id):
    """
    Generate HTML page with detail data about test action

    **Template:**

    :template:`test_report/action_details.html`
    """

    action_aggregate_data = list(
        TestActionAggregateData.objects.annotate(
            test_name=F('test__name')).filter(
                action_id=action_id, test_id__lte=test_id).values(
                    'test_name', 'data').order_by('-test__started_at'))[:5]
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
    test_started_at = TestActionData.objects. \
        filter(test_id=test_id, data_resolution_id=1). \
        aggregate(min_timestamp=Min(
            RawSQL(
                "((data->>%s)::timestamp)",
                ('timestamp',)))
            )['min_timestamp']
    test_errors = TestError.objects.annotate(
        text=F('error__text'), code=F('error__code')).filter(
            test_id=test_id, action_id=action_id).values(
                'text', 'code', 'count')
    return render(
        request,
        'analyzer/report/test_report/action_details.html', {
            'test_id': test_id,
            'action': Action.objects.get(id=action_id),
            'action_data': action_data,
            'test_started_at': test_started_at,
            'test_errors': test_errors,
        })


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
        project = Project(name="New project", )
        project.save()
        project_id = project.id
    test = Test(
        project_id=project_id,
        display_name=test_name,
        show=True,
        started_at=int(time.time() * 1000))
    test.save()
    test_id = test.id
    path = default_storage.save('test_result_data.csv',
                                ContentFile(csv_file.read()))
    csv_file_fields = csv_file_fields.split(',')
    generate_test_results_data(test_id,
                               project_id, path,
                               jmeter_results_file_fields=csv_file_fields)

    return render(request, "upload/success.html", {
        'result': 'ok',
        'test_name': test_name,
        'project_id': project_id,
    })

def get_test_for_project(project_id, n):
    '''
    Get first, second, N test for project with project_id
    '''
    t = list(Test.objects.filter(project__id=project_id)\
        .order_by('-started_at').values())[n]
    return t


def project_history(request, project_id):
    '''
    Return whole list of tests with avg and median response times
    for project_id
    '''
    source = 'default'

    data = TestData.objects. \
        filter(test__project_id=project_id,
               test__show=True,
               source=source,
               data_resolution_id=1).\
        annotate(test_name=F('test__display_name')). \
        values('test_name'). \
        annotate(mean=Sum(RawSQL("((data->>%s)::numeric)", ('avg',)) *
                          RawSQL("((data->>%s)::numeric)", ('count',))) /
                          Sum(RawSQL("((data->>%s)::numeric)", ('count',)))). \
        annotate(median=Sum(RawSQL("((data->>%s)::numeric)", ('median',))*RawSQL("((data->>%s)::numeric)", ('count',)))/Sum(RawSQL("((data->>%s)::numeric)", ('count',)))). \
        order_by('test__started_at')
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
    started_at = Test.objects.filter(
        id=test_id).values('started_at')[0]['started_at']
    t = Test.objects.filter(started_at__lte=started_at, project=p).\
        values('id').order_by('-started_at')
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
    test = Test.objects.get(id=test_id)
    aggregate_table = get_test_aggregate_table(test_id)
    return render(request, 'report.html', {
        'test': test,
        'aggregate_table': aggregate_table
    })


def action_report(request, test_id, action_id):
    '''
    Generate HTML page with detail data about some action
    which were execute during the test
    '''

    action_aggregate_data = list(
        TestActionAggregateData.objects.annotate(
            test_name=F('test__display_name')).filter(
                action_id=action_id, test_id__lte=test_id).values(
                    'test_name', 'data').order_by('-test__started_at'))[:5]
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
    test_started_at = TestActionData.objects. \
        filter(test_id=test_id, data_resolution_id=1). \
        aggregate(min_timestamp=Min(
            RawSQL("((data->>%s)::timestamp)",
                  ('timestamp',))))['min_timestamp']
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
            'test_started_at': test_started_at,
            'test_errors': test_errors,
        })


def action_rtot(request, test_id, action_id):
    '''Return response times over time data for the action'''
    min_timestamp = TestActionData.objects. \
        filter(test_id=test_id, action_id=action_id, data_resolution_id=1). \
        values("test_id", "action_id"). \
        aggregate(min_timestamp=Min(
            RawSQL("((data->>%s)::timestamp)",
                  ('timestamp',))))['min_timestamp']
    x = TestActionData.objects. \
        filter(test_id=test_id, action_id=action_id, data_resolution_id=1). \
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
        filter(test_id=test_id, server_id=server_id, source=source,
               data_resolution_id=1).values('data')[:1]
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
        filter(servermonitoringdata__test_id=test_id,
               servermonitoringdata__source=source,
               servermonitoringdata__data_resolution_id=1).\
        values().distinct()

    return JsonResponse(list(servers_list), safe=False)


def test_edit_page(request, test_id):
    '''Generate test edit HTML page '''

    test = Test.objects.filter(id=test_id).values()
    return render(request, 'test/edit.html', {
        'test': test[0],
    })


def test_change(request, test_id):
    '''Change test data'''
    test = Test.objects.get(id=test_id)
    response = []
    if request.method == 'POST':
        if 'edit_param' in request.POST:
            edit_param = request.POST.get('edit_param', '')
            edit_val = request.POST.get('edit_val', '')
            if 'show' in edit_param:
                edit_val = request.POST.get('edit_val', '')
                test.show = True if edit_val == 'true' else False
                test.save()
            else:
                setattr(test, edit_param, edit_val)
                test.save()
            response = {
                'message': {
                    'text': 'Test data was chaged',
                    'type': 'success',
                    'msg_params': {
                        'test_id': test_id,
                        'edit_param': edit_param,
                    }
                }
            }
    return JsonResponse(response, safe=False)


def get_compare_tests_server_monitoring_data(test_id,
                                             num_of_tests,
                                             order='-test__started_at'):
    '''Return cpu load data for N tests before the current one'''

    project = Test.objects.filter(id=test_id).values('project_id')
    project_id = project[0]['project_id']
    started_at = Test.objects.filter(
        id=test_id).values('started_at')[0]['started_at']
    data = (ServerMonitoringData.objects.filter(
        test__started_at__lte=started_at,
        test__project_id=project_id,
        test__show=True,
        data_resolution_id=1,
        source='default',
    ).values(
        'test__display_name', 'server__server_name', 'test__started_at'
    ).annotate(
        cpu_load=RawSQL(
            "((data->>%s)::float)+((data->>%s)::float)+((data->>%s)::float)", (
                'CPU_user',
                'CPU_iowait',
                'CPU_system',
            ))).annotate(
                cpu_load=Avg('cpu_load')).order_by('-test__started_at'))
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
            if int(d['test__started_at']) == int(
                    data[counter - 1]['test__started_at']):
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
    if response:
        response = to_pivot(response, 'test__display_name',
                            'server__server_name', 'cpu_load')
        response = response.to_json(orient='index')
    # return HttpResponse(response)
    return HttpResponse(
        json.loads(
            json.dumps(response, sort_keys=False),
            object_pairs_hook=OrderedDict))


def get_compare_tests_aggregate_data(test_id,
                                     num_of_tests,
                                     order='-test__started_at',
                                     source='default'):
    '''
    Compares given test with test_id against num_of_tests previous
    '''
    project = Test.objects.filter(id=test_id).values('project_id')
    started_at = Test.objects.filter(
        id=test_id).values('started_at')[0]['started_at']
    project_id = project[0]['project_id']
    if source == 'default':
        data = TestData.objects. \
                filter(test__started_at__lte=started_at,
                       test__project_id=project_id, test__show=True,
                       source=source, data_resolution_id = 1).\
                annotate(display_name=F('test__display_name')). \
                annotate(started_at=F('test__started_at')). \
                values('display_name', 'started_at'). \
                annotate(average=Sum(RawSQL("((data->>%s)::numeric)", ('avg',))*RawSQL("((data->>%s)::numeric)", ('count',)))/Sum(RawSQL("((data->>%s)::numeric)", ('count',)))). \
                annotate(median=Sum(RawSQL("((data->>%s)::numeric)", ('median',))*RawSQL("((data->>%s)::numeric)", ('count',)))/Sum(RawSQL("((data->>%s)::numeric)", ('count',)))). \
                order_by(order)[:int(num_of_tests)]
    elif source == 'graphite':
        tests = Test.objects.filter(
            started_at__lte=started_at, project_id=project_id,
            show=True).values().order_by('-started_at')[:int(num_of_tests)]
        for t in tests:
            test_id = t['id']
            if not ServerMonitoringData.objects.filter(
                    test_id=test_id, source='graphite', data_resolution_id=1
            ).exists() or not TestData.objects.filter(
                    test_id=test_id, source='graphite',
                    data_resolution_id=1).exists():
                result = update_test_graphite_data(test_id)
        data = TestData.objects. \
                filter(test__started_at__lte=started_at,
                       test__project_id=project_id, test__show=True,
                       source=source, data_resolution_id = 1).\
                annotate(display_name=F('test__display_name')). \
                annotate(started_at=F('test__started_at')). \
                values('display_name', 'started_at'). \
                annotate(average=Avg(RawSQL("((data->>%s)::numeric)", ('avg',)))). \
                annotate(median=Avg(RawSQL("((data->>%s)::numeric)", ('median',)))). \
                order_by(order).order_by(order)[:int(num_of_tests)]
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
                if int(d['started_at']) == int(
                        data[counter - 1]['started_at']):
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


def get_compare_tests_count(test_id,
                            num_of_tests,
                            order='-test__started_at',
                            source='default'):
    '''
    Compares given test with test_id against num_of_tests previous
    '''
    project = Test.objects.filter(id=test_id).values('project_id')
    started_at = Test.objects.filter(
        id=test_id).values('started_at')[0]['started_at']
    project_id = project[0]['project_id']
    data = TestActionData.objects.filter(
                test__started_at__lte=started_at,
                test__project_id=project_id,
                test__show=True,
                data_resolution_id=1
            ).annotate(
                display_name=F('test__display_name')
            ).annotate(
                started_at=F('test__started_at')
            ).values(
                'display_name', 'started_at'
            ).annotate(
                count=Sum(RawSQL("((data->>%s)::numeric)", ('count',)))
            ).annotate(
                errors=Sum(RawSQL("((data->>%s)::numeric)", ('errors',)))
            ).order_by(order)[:int(num_of_tests)]

    return data

def compare_tests_count(request, test_id):
    '''
    Compare amount of requests and errors from current and N previous tests
    '''
    if request.method == 'POST':
        source = request.POST.get('source', '0')
        num_of_tests = request.POST.get('num_of_tests_to_compare', '0')
        data = get_compare_tests_count(test_id, num_of_tests, source=source)
        current_rank = 1
        counter = 0
        arr = []
        for d in data:
            if counter < 1:
                d['rank'] = current_rank
            else:
                if int(d['started_at']) == int(
                        data[counter - 1]['started_at']):
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
        data_resolution_id = int(request.POST.get('data_resolution_id', '1'))
        data_resolution = TestDataResolution.objects.get(id=data_resolution_id)
        if source == 'default':
            # If there is no data for required resolution, then re-generate data
            if not TestData.objects.filter(
                    test_id=test_id,
                    source='default',
                    data_resolution_id=data_resolution_id).exists():
                jmeter_results_file_dest = unpack_test_results_data(test_id)
                project_id = Test.objects.get(id=test_id).project_id
                generate_test_results_data(
                    test_id,
                    project_id,
                    jmeter_results_file_path=jmeter_results_file_dest,
                    data_resolution=data_resolution.frequency)
        min_timestamp = TestData.objects. \
            filter(test_id=test_id, source=source,
                   data_resolution_id=data_resolution_id). \
            values("test_id").\
            aggregate(min_timestamp=Min(
                RawSQL("((data->>%s)::timestamp)", ('timestamp',))))['min_timestamp']
        x = TestData.objects. \
            filter(test_id=test_id, source=source,
                   data_resolution_id=data_resolution_id). \
            annotate(timestamp=(RawSQL("((data->>%s)::timestamp)", ('timestamp',)) - min_timestamp)). \
            annotate(average=RawSQL("((data->>%s)::numeric)", ('avg',))). \
            annotate(median=RawSQL("((data->>%s)::numeric)", ('median',))). \
            annotate(rps=(RawSQL("((data->>%s)::numeric)", ('count',))) / data_resolution.per_sec_divider). \
            values('timestamp', "average", "median", "rps"). \
            order_by('timestamp')
        data = json.loads(
            json.dumps(list(x), indent=4, sort_keys=True, default=str))
        return JsonResponse(data, safe=False)


def test_errors(request, test_id):
    '''
    Return overall success/errors percentage
    '''

    data = TestActionAggregateData.objects. \
                filter(test_id=test_id). \
                annotate(errors=RawSQL("((data->>%s)::numeric)", ('errors',))). \
                annotate(count=RawSQL("((data->>%s)::numeric)", ('count',))). \
                aggregate(count_sum=Sum(F('count'),
                          output_field=FloatField()),
                          errors_sum=Sum(F('errors'),
                          output_field=FloatField())
                         )
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
                order_by('-average').values('url', 'average')[:int(top_number)]
    return JsonResponse(list(data), safe=False)


def test_top_errors(request, test_id):
    '''
    Return top N actions with highest errors percentage
    '''

    data = TestActionAggregateData.objects.filter(test_id=test_id). \
        annotate(url=F('action__url')). \
        annotate(errors=Round(RawSQL(
                 "((data->>%s)::numeric)", ('errors',)) * 100 / RawSQL("((data->>%s)::numeric)", ('count',)))). \
        order_by('-errors').values('url', 'action_id', 'errors')[:5]
    return JsonResponse(list(data), safe=False)


def metric_max_value(request, test_id, server_id, metric):
    '''Return maximum value for some metric'''

    max_value = {}
    if 'CPU' in metric:
        max_value = {'max_value': 100}
    else:
        max_value = ServerMonitoringData.objects. \
            filter(test_id=test_id, server_id=server_id,
                   data_resolution_id=1).\
            annotate(val=RawSQL("((data->>%s)::numeric)", (metric,))).\
            aggregate(max_value=Max('val', output_field=FloatField()))
    return JsonResponse(max_value, safe=False)


def tests_compare_aggregate_new(request, test_id_1, test_id_2):
    '''Return comparasion data for all actions in two tests'''
    response = []
    action_data_1 = TestActionAggregateData.objects.annotate(
        action_name=F('action__url')).annotate(
            mean=RawSQL("((data->>%s)::numeric)", (
                'mean', ))).filter(test_id=test_id_1).values(
                    'action_id', 'action_name', 'mean')
    for action in action_data_1:
        action_id = action['action_id']
        if TestActionAggregateData.objects.filter(
                action_id=action_id, test_id=test_id_2).exists():
            action_data_2 = TestActionAggregateData.objects.annotate(
                action_name=F('action__url')).annotate(
                    mean=RawSQL("((data->>%s)::numeric)", ('mean', ))).filter(
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
            test_id=test_id, source='graphite',
            data_resolution_id=1).exists() or not TestData.objects.filter(
                test_id=test_id, source='graphite',
                data_resolution_id=1).exists():
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
                RawSQL("((data->>%s)::timestamp)",
                      ('timestamp',))))['min_timestamp']

        if metric == 'CPU_all':
            metric_mapping = {
                metric:
                RawSQL("(((data->>%s)::numeric)+((data->>%s)::numeric)+"
                       "((data->>%s)::numeric))", (
                           'CPU_iowait',
                           'CPU_user',
                           'CPU_system',
                       ))
            }
        else:
            metric_mapping = {
                metric: RawSQL("((data->>%s)::numeric)", (metric, ))
            }
        x = ServerMonitoringData.objects. \
            filter(test_id=test_id, server_id=server_id,
                   source=source, data_resolution_id=1). \
            annotate(timestamp=RawSQL("((data->>%s)::timestamp)",
                    ('timestamp',)) - min_timestamp).\
            annotate(**metric_mapping). \
            values('timestamp', metric)
        data = json.loads(
            json.dumps(list(x), indent=4, sort_keys=True, default=str))
    return JsonResponse(data, safe=False)


def action_graphs(request, test_id):
    actions_list = list(
        TestActionAggregateData.objects.annotate(name=F('action__url')).filter(
            test_id=test_id).values('action_id', 'name'))
    return render(request, 'action_graphs.html', {
        'actions_list': actions_list,
        'test_id': test_id
    })


def dashboard_compare_tests_list(tests_list):
    '''Return comparasion data for dashboard'''
    tests = []
    for t in tests_list:
        test_id = t['id']
        project_id = t['project_id']
        project = Project.objects.get(id=project_id)

        project_tests = Test.objects.filter(
            project=project, id__lte=test_id).order_by('-started_at')

        if project_tests.count() > 1:
            prev_test_id = project_tests[1].id
        else:
            prev_test_id = test_id
        test_data = TestActionAggregateData.objects.filter(test_id=test_id). \
            annotate(errors=RawSQL("((data->>%s)::numeric)", ('errors',))). \
            annotate(count=RawSQL("((data->>%s)::numeric)", ('count',))). \
            annotate(weight=RawSQL("((data->>%s)::numeric)", ('weight',))). \
            aggregate(count_sum=Sum(F('count'), output_field=FloatField()),
                      errors_sum=Sum(F('errors'), output_field=FloatField()),
                      overall_avg=Sum(F('weight')) / Sum(F('count')))

        prev_test_data = TestActionAggregateData.objects. \
            filter(test_id=prev_test_id). \
            annotate(errors=RawSQL("((data->>%s)::numeric)", ('errors',))). \
            annotate(count=RawSQL("((data->>%s)::numeric)", ('count',))). \
            annotate(weight=RawSQL("((data->>%s)::numeric)", ('weight',))). \
            aggregate(
                count_sum=Sum(F('count'), output_field=FloatField()),
                errors_sum=Sum(F('errors'), output_field=FloatField()),
                overall_avg=Sum(F('weight')) / Sum(F('count'))
                )
        try:
            errors_percentage = test_data['errors_sum'] * 100 / test_data[
                'count_sum']
        except (TypeError, ZeroDivisionError) as e:
            logger.error(e)
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
            t['project__name'],
            'name':
            t['name'],
            'vars':
            t['vars'],
            'started_at':
            t['started_at'],
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

def queryset_to_json(set):
    return json.loads(
        json.dumps(list(set), indent=4, sort_keys=True, default=str))
