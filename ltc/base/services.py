"""
Dashboard statistics shared by the legacy dashboard view and the DRF API.
"""
import logging

from django.db.models import F, FloatField, Sum
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast

from ltc.analyzer.models import TestActionAggregateData
from ltc.base.models import Test

logger = logging.getLogger('django')

# Success-rate severity thresholds (percent of non-failed requests).
SUCCESS_WARNING_PERCENT = 98
SUCCESS_CRITICAL_PERCENT = 95


def success_level(success_requests):
    if success_requests >= SUCCESS_WARNING_PERCENT:
        return 'success'
    if success_requests >= SUCCESS_CRITICAL_PERCENT:
        return 'warning'
    return 'danger'


def aggregate_test_stats(test_ids):
    """
    One grouped query: {test_id: {'count_sum', 'errors_sum', 'mean'}}
    computed from the JSONB per-action aggregates.
    """
    def _key(name):
        return Sum(
            Cast(KeyTextTransform(name, 'data'), FloatField())
        )

    rows = (
        TestActionAggregateData.objects
        .filter(test_id__in=test_ids)
        .values('test_id')
        .annotate(
            count_sum=_key('count'),
            errors_sum=_key('errors'),
            weight_sum=_key('weight'),
        )
    )
    stats = {}
    for row in rows:
        count_sum = row['count_sum'] or 0
        weight_sum = row['weight_sum'] or 0
        stats[row['test_id']] = {
            'count_sum': count_sum,
            'errors_sum': row['errors_sum'] or 0,
            'mean': (weight_sum / count_sum) if count_sum else None,
        }
    return stats


def previous_test_ids(tests):
    """{test_id: previous finished test id in the same project} (one query)."""
    project_ids = {t.project_id for t in tests if t.project_id}
    rows = (
        Test.objects.filter(project_id__in=project_ids)
        .order_by(
            'project_id', F('started_at').desc(nulls_last=True), '-id'
        )
        .values_list('id', 'project_id')
    )
    by_project = {}
    for test_id, project_id in rows:
        by_project.setdefault(project_id, []).append(test_id)
    prev = {}
    for test in tests:
        ordered = by_project.get(test.project_id, [])
        try:
            idx = ordered.index(test.id)
        except ValueError:
            continue
        if idx + 1 < len(ordered):
            prev[test.id] = ordered[idx + 1]
    return prev


SPARK_POINTS = 12


def sparklines(tests):
    """
    {test_id: [mean, ...]} — the recent per-test mean response times of the
    same project, oldest→newest, ending at that test (dashboard sparkline).

    Batched: two queries total regardless of how many tests are on the page.
    """
    tests = [t for t in tests if t is not None and t.project_id]
    if not tests:
        return {}
    project_ids = {t.project_id for t in tests}

    # Every test of those projects, newest first, so we can take a window
    # ending at each test we were asked about.
    ordered = list(
        Test.objects.filter(project_id__in=project_ids)
        .order_by('project_id', F('started_at').desc(nulls_last=True), '-id')
        .values_list('id', 'project_id')
    )
    by_project = {}
    for test_id, project_id in ordered:
        by_project.setdefault(project_id, []).append(test_id)

    # One aggregate query for every test id we might need a mean for.
    needed = set()
    for test in tests:
        window = by_project.get(test.project_id, [])
        try:
            index = window.index(test.id)
        except ValueError:
            continue
        needed.update(window[index:index + SPARK_POINTS])
    means = {
        test_id: row['mean']
        for test_id, row in aggregate_test_stats(needed).items()
    }

    result = {}
    for test in tests:
        window = by_project.get(test.project_id, [])
        try:
            index = window.index(test.id)
        except ValueError:
            result[test.id] = []
            continue
        # oldest → newest, so reverse the newest-first window
        series = [
            round(means[test_id], 1)
            for test_id in reversed(window[index:index + SPARK_POINTS])
            if means.get(test_id) is not None
        ]
        result[test.id] = series
    return result


def dashboard_test_stats(tests):
    """
    Per-test dashboard stats incl. comparison with the previous test of the
    same project, in a constant number of queries.

    Returns {test_id: {'test_data', 'prev_test_id', 'prev_test_data',
                       'success_requests', 'result'}}
    """
    tests = [t for t in tests if t is not None]
    prev_ids = previous_test_ids(tests)
    all_ids = {t.id for t in tests} | set(prev_ids.values())
    stats = aggregate_test_stats(all_ids)
    result = {}
    for test in tests:
        test_data = stats.get(test.id, {})
        prev_test_id = prev_ids.get(test.id)
        try:
            errors_percentage = (
                test_data['errors_sum'] * 100 / test_data['count_sum']
            )
        except (KeyError, TypeError, ZeroDivisionError):
            errors_percentage = 0
        success_requests = 100 - errors_percentage
        result[test.id] = {
            'test_data': test_data,
            'prev_test_id': prev_test_id,
            'prev_test_data': stats.get(prev_test_id, {}),
            'success_requests': success_requests,
            'result': success_level(success_requests),
        }
    return result
