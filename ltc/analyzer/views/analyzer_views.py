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
@login_required
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
        return render(
            request, 'upload/test_result_file.html',
            {'projects': projects}
        )
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
    generate_test_results_data(
        test_id,
        project_id, path,
        jmeter_results_file_fields=csv_file_fields
    )

    return render(request, "upload/success.html", {
        'result': 'ok',
        'test_name': test_name,
        'project_id': project_id,
    })


def queryset_to_json(set):
    return json.loads(
        json.dumps(list(set), indent=4, sort_keys=True, default=str))
