"""
Report/comparison payload builders shared by the legacy template views and
the DRF API (ltc.api). Keep this module free of HTTP concerns.
"""
import logging
import math

from django.db.models import DateTimeField, Min
from django.db.models.expressions import F
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast
from scipy import stats

from ltc.analyzer.models import (
    Action,
    TestActionAggregateData,
    TestActionData,
    TestError,
)
from ltc.base.models import Configuration, Test

logger = logging.getLogger('django')

# Aggregate-table error-percentage severity bands (UI colouring).
ERRORS_WARNING_PERCENT = 3
ERRORS_CRITICAL_PERCENT = 10
# Actions slower than this are highlighted in the top-mean chart.
SLOW_ACTION_THRESHOLD_MS = 200


def test_report_data(test):
    """The full analyzer report payload for one test (JSON-serializable)."""
    test = (
        Test.objects.filter(id=test.id)
        .prefetch_related(
            'testdata_set',
            'testactionaggregatedata_set',
            'testactiondata_set',
            'servermonitoringdata_set',
        )
        .first()
    )
    response = {'test_id': test.id, 'name': test.name}
    test_action_aggregate_data = []
    for d in test.testactionaggregatedata_set.select_related('action').all():
        d_ = d.data
        d_['action'] = d.action.name
        d_['action_id'] = d.action_id
        d_['errors_level'] = _errors_level(d_)
        test_action_aggregate_data.append(d_)

    test_data = [d.data for d in test.testdata_set.all()]

    server_monitoring_data = {}
    for d in test.servermonitoringdata_set.select_related('server').all():
        server_monitoring_data.setdefault(
            d.server.server_name.replace('.', '_'), []
        ).append(d.data)

    # A test that never started has no started_at; fall back to id order.
    prev_tests = Test.objects.filter(project=test.project)
    if test.started_at is not None:
        prev_tests = prev_tests.filter(started_at__lte=test.started_at)
    else:
        prev_tests = prev_tests.filter(id__lte=test.id)
    prev_tests = prev_tests.order_by(
        F('started_at').desc(nulls_last=True)
    )[:15]
    compare_data = []
    for t in prev_tests:
        if not t.get_test_metric('mean'):
            continue
        test_name = t.name or f'{t.project.name} - {t.id}'
        compare_data.append(
            {
                'test_id': t.id,
                'test_name': test_name,
                'mean': t.get_test_metric('mean')[0]['mean'],
                'median': t.get_test_metric('median')[0]['median'],
                'cpu_load': t.get_test_metric('cpu_load'),
            }
        )
    response['test_action_aggregate_data'] = test_action_aggregate_data
    response['test_data'] = test_data
    response['server_monitoring_data'] = server_monitoring_data
    response['compare_data'] = compare_data
    response['slow_action_threshold_ms'] = SLOW_ACTION_THRESHOLD_MS
    return response


def _errors_level(data):
    try:
        errors_percent = float(data['errors']) * 100 / float(data['count'])
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return 'ok'
    if errors_percent >= ERRORS_CRITICAL_PERCENT:
        return 'crit'
    if errors_percent >= ERRORS_WARNING_PERCENT:
        return 'warn'
    return 'ok'


def compare_table(tests):
    """Side-by-side per-action stats for two tests."""
    table = []
    if len(tests) < 2:
        return table
    action_data_1 = TestActionAggregateData.objects.annotate(
        name=F('action__name')
    ).filter(test_id=tests[0].id).values(
        'action_id',
        'name',
        'data',
    )
    for action in action_data_1:
        action_id = action['action_id']
        action_data_2 = TestActionAggregateData.objects.annotate(
            name=F('action__name')
        ).filter(
            action_id=action_id, test_id=tests[1].id
        ).values('action_id', 'name', 'data').first()
        if action_data_2 is None:
            continue
        table.append({
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
    return table


def resolve_compare_tests(test_ids):
    """Resolve [current, other] tests from a list of ids (other optional)."""
    tests = []
    test = Test.objects.get(id=test_ids[0])
    tests.append(test)
    if len(test_ids) < 2 or int(test_ids[1]) <= 0:
        tests.append(test.prev_test())
    else:
        tests.append(Test.objects.get(id=test_ids[1]))
    return tests


def compare_highlights(tests):
    """
    Comparison highlights between tests[0] (current) and tests[1] (other):
    new/absent actions, and actions whose mean response time changed
    significantly per Student's t-test (Satterthwaite degrees of freedom).
    """
    highlights = {'critical': [], 'warning': [], 'success': []}
    actions = {}
    actions_data = {}
    for test in tests:
        actions[test.id] = TestActionAggregateData.objects.annotate(
            name=F('action__name')
        ).filter(test=test).values('name', 'action_id')
        actions_data[test.id] = TestActionAggregateData.objects.annotate(
            name=F('action__name')
        ).filter(test=test).values('name', 'data')
    highlights['warning'] = [
        {'action': action, 'type': 'new_actions'}
        for action in actions[tests[0].id]
        if action not in actions[tests[1].id]
    ] + [
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
        action = {'other_test': a}
        action_name = action['other_test']['name']
        a_ = actions_data[tests[0].id].filter(name=action_name)
        if a_.first() is None:
            continue
        action['current_test'] = a_.first()

        # Student t-criteria
        Xa = action['current_test']['data']['mean']
        Xb = action['other_test']['data']['mean']
        Sa = action['current_test']['data']['std'] or 0
        Sb = action['other_test']['data']['std'] or 0
        Na = action['current_test']['data']['count']
        Nb = action['other_test']['data']['count']
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
    return highlights


def action_details_data(test_id, action_id):
    """Per-action stats (incl. boxplot data) and errors for a test."""
    action_aggregate_data = list(
        TestActionAggregateData.objects.annotate(
            test_name=F('test__name')).filter(
                action_id=action_id, test_id__lte=test_id).values(
                    'test_name', 'data').order_by('-test__started_at'))[:5]
    action_data = []
    for e in action_aggregate_data:
        data = e['data']
        q3 = data['75%']
        q2 = data['50%']
        # Old data may lack the 25th percentile; mirror it around the median.
        q1 = data.get('25%', q2 - (q3 - q2))
        iqr = q3 - q1
        lw = max(q1 - 1.5 * iqr, 0.1)
        uw = q3 + 1.5 * iqr
        action_data.append({
            'q1': q1,
            'q2': q2,
            'q3': q3,
            'IQR': iqr,
            'LW': lw,
            'UW': uw,
            'mean': data['mean'],
            'min': data['min'],
            'max': data['max'],
            'std': data['std'],
            'test_name': e['test_name'],
        })
    test_started_at = TestActionData.objects. \
        filter(test_id=test_id, data_resolution_id=1). \
        aggregate(min_timestamp=Min(
            Cast(KeyTextTransform('timestamp', 'data'), DateTimeField()))
            )['min_timestamp']
    test_errors = list(
        TestError.objects.annotate(
            text=F('error__text'), code=F('error__code')).filter(
                test_id=test_id, action_id=action_id).values(
                    'text', 'code', 'count')
    )
    return {
        'test_id': test_id,
        'action': Action.objects.get(id=action_id),
        'action_data': action_data,
        'test_started_at': test_started_at,
        'test_errors': test_errors,
    }
