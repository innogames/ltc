# -*- coding: utf-8 -*-
import json
import logging
import math
import time
from collections import OrderedDict

import pandas as pd
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Avg, FloatField, Func, Max, Min, Sum
from django.db.models.expressions import F, RawSQL
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.generic import TemplateView
from scipy import stats

from jltc.models import Configuration
from analyzer.confluence import confluenceposter
from analyzer.confluence.utils import generate_confluence_graph
from analyzer.models import (Action, Project, Server, ServerMonitoringData,
                             Test, TestActionAggregateData, TestActionData,
                             TestData, TestDataResolution, TestError)
from django.views.decorators.http import require_POST
from django.forms.models import model_to_dict

logger = logging.getLogger(__name__)

def index(request):
    context = {}
    context['projects'] = Project.objects.distinct()
    if request.method == 'POST':
        project_id = request.POST.get('project_id', '')
        test_id = request.POST.get('test_id', '')
        if project_id:
            context['project_'] = Project.objects.get(id=project_id)
            context['tests'] = Test.objects.filter(project_id=project_id)
        if test_id:
            context['test_'] = Test.objects.get(id=test_id)
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
    response['display_name'] = data.display_name
    test_action_aggregate_data = []
    for d in data.testactionaggregatedata_set.all():
        d_ = d.data
        d_['action'] = d.action.url
        test_action_aggregate_data.append(d_)
    test_data = []
    for d in data.testdata_set.all():
        d_= d.data
        test_data.append(d_)

    server_monitoring_data = {}
    for d in data.servermonitoringdata_set.all():
        d_= d.data
        server_monitoring_data.setdefault(
            d.server.server_name.replace(".", "_"), []
        ).append(d_)

    prev_tests = Test.objects.filter(start_time__lte=data.start_time,
        project_id=data.project_id, show=True,
    ).order_by('-start_time')
    compare_data = []
    for t in prev_tests:
        compare_data.append(
            {
                'test_name': t.display_name,
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
        tests.append(Test.objects.get(id=test_ids[1]))
    highlights = {}
    highlights['critical'] = []
    highlights['warning'] = []
    highlights['success'] = []
    actions = {}
    actions_data = {}
    for test in tests:
        actions[
            test.display_name
        ] = TestActionAggregateData.objects.annotate(
            url=F('action__url')
        ).filter(test=test).values('url', 'action_id')
        actions_data[
            test.display_name
        ] = TestActionAggregateData.objects.annotate(
            url=F('action__url')
        ).filter(test=test).values('url', 'data')

    highlights['warning'] = [
        {'action': action, 'type': 'new_actions'}
        for action in actions[tests[0].display_name]
        if action not in actions[tests[1].display_name]
    ]

    highlights['warning'] = [
        {'action': action, 'type': 'absent_actions'}
        for action in actions[tests[1].display_name]
        if action not in actions[tests[0].display_name]
    ]

    sp = int(Configuration.objects.get(
        name='signifficant_actions_compare_percent'
        ).value)

    for a in actions_data[tests[1].display_name]:
        action = {}
        action['other_test'] = a
        action_url = action['other_test']['url']
        a_ = actions_data[
            tests[0].display_name
        ].filter(url=action_url)
        if a_.first() is None:
            continue
        action['current_test'] = a_.first()
        Xa = action['current_test']['data']['mean']
        Xb = action['other_test']['data']['mean']
        Sa = action['current_test']['data'].get('std', 0)
        Sb = action['other_test']['data'].get('std', 0)
        Na = action['current_test']['data']['count']
        Nb = action['other_test']['data']['count']
        # df = Na - 1 + Nb - 1
        # Satterthwaite Formula for Degrees of Freedom
        critical = []
        if Xa > 10 and Xb > 10 and not Sa == 0 and not Sb == 0:
            df = math.pow(
                math.pow(Sa, 2) / Na + math.pow(Sb, 2) / Nb, 2) / (
                    math.pow(math.pow(Sa, 2) / Na, 2) /
                    (Na - 1) + math.pow(math.pow(Sb, 2) / Nb, 2) /
                    (Nb - 1))
            if df > 0:
                t = stats.t.ppf(1 - 0.01, df)
                Sab = math.sqrt(((Na - 1) * math.pow(Sa, 2) +
                                    (Nb - 1) * math.pow(Sb, 2)) / df)
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
            test_name=F('test__display_name')).filter(
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
        'analyzer/report/test_report/action_details.html', {
            'test_id': test_id,
            'action': Action.objects.get(id=action_id),
            'action_data': action_data,
            'test_start_time': test_start_time,
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
        project = Project(project_name="New project", )
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
    csv_file_fields = csv_file_fields.split(',')
    generate_test_results_data(test_id,
                               project_id, path,
                               jmeter_results_file_fields=csv_file_fields)

    return render(request, "upload/success.html", {
        'result': 'ok',
        'test_name': test_name,
        'project_id': project_id,
    })


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
                        filter(test_id=test_id, action_id=action_id,
                               data_resolution_id=1). \
                        values("test_id", "action_id"). \
                        aggregate(min_timestamp=Min(
                            RawSQL("((data->>%s)::timestamp)",
                                  ('timestamp',))))['min_timestamp']

                    mapping = {
                        col_name: RawSQL("((data->>%s)::numeric)", ('avg', ))
                    }
                    action_data = list(TestActionData.objects.
                        filter(test_id=test_id,
                               action_id=action_id, data_resolution_id=1). \
                        annotate(timestamp=(RawSQL("((data->>%s)::timestamp)",
                                ('timestamp',)) - min_timestamp)).
                        annotate(**mapping).
                        values('timestamp', col_name).
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
    return JsonResponse([get_test_for_project(project_id, 0)], safe=False)


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
    return JsonResponse([list(t)[1]], safe=False)




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
        TestActionAggregateData.objects.annotate(
            test_name=F('test__display_name')).filter(
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
            'test_start_time': test_start_time,
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
        last_test['id'], 10, order='-start_time')
    agg_response_times_graph = generate_confluence_graph(project, list(data))
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

    target_page = project.confluence_page

    if not target_page:
        target_page = '{0} Load Testing Reports'.format(project.project_name)

    target_url = '{}/display/{}/{}'.format(wiki_url, space, target_page)

    # Post parent summary page
    try:
        logger.info('Try to open Confluence page: {}: {}'.format(
            target_page, target_url))
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
        page_title = target_page + ' - ' + test_name
        test_report_page_exists = True
        try:
            page_test_report = cp.get_page(space, page_title)
        except Exception as e:
            test_report_page_exists = False
            page_test_report = page_parent
            page_test_report['parentId'] = page_parent_id
            page_test_report['title'] = page_title
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
            'message': {
                'text':
                'Project report is posted to Confluence: {}'.format(
                    target_url),
                'type':
                'success',
                'msg_params': {
                    'link': target_url
                }
            }
        }
    else:
        response = {
            'message': {
                'text': 'Report was not posted: {}'.format(error),
                'type': 'danger',
                'msg_params': {
                    'link': target_url
                }
            }
        }

    return JsonResponse(response, safe=False)


def queryset_to_json(set):
    return json.loads(
        json.dumps(list(set), indent=4, sort_keys=True, default=str))
