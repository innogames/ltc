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

from jltc.models import Configuration, Test, Project
from analyzer.confluence import confluenceposter
from analyzer.confluence.utils import generate_confluence_graph
from analyzer.models import (
    Action, Server, ServerMonitoringData,
    TestActionAggregateData, TestActionData,
    TestData, TestDataResolution, TestError
)
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
    response['name'] = data.name
    test_action_aggregate_data = []
    for d in data.testactionaggregatedata_set.all():
        d_ = d.data
        d_['action'] = d.action.name
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

    prev_tests = Test.objects.filter(
        started_at__lte=data.started_at,
        project_id=data.project_id,
    ).order_by('-started_at')
    compare_data = []
    for t in prev_tests:
        compare_data.append(
            {
                'test_name': t.name,
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
            test.name
        ] = TestActionAggregateData.objects.annotate(
            name=F('action__name')
        ).filter(test=test).values('name', 'action_id')
        actions_data[
            test.name
        ] = TestActionAggregateData.objects.annotate(
            name=F('action__name')
        ).filter(test=test).values('name', 'data')

    highlights['warning'] = [
        {'action': action, 'type': 'new_actions'}
        for action in actions[tests[0].name]
        if action not in actions[tests[1].name]
    ]

    highlights['warning'] = [
        {'action': action, 'type': 'absent_actions'}
        for action in actions[tests[1].name]
        if action not in actions[tests[0].name]
    ]

    sp = int(Configuration.objects.get(
        name='signifficant_actions_compare_percent'
        ).value)

    for a in actions_data[tests[1].name]:
        action = {}
        action['other_test'] = a
        action_name = action['other_test']['name']
        a_ = actions_data[
            tests[0].name
        ].filter(name=action_name)
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
            'test_started_at': test_started_at,
            'test_errors': test_errors,
        })
