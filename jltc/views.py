import json
import logging
import time
from datetime import datetime, timedelta

from django.db.models import Avg, FloatField, Func, Max, Min, Sum
from django.db.models.expressions import F, RawSQL
from django.shortcuts import render

from analyzer.models import (
    Action, Server, ServerMonitoringData, TestActionAggregateData,
    TestActionData, TestData, TestDataResolution, TestError)
from jltc.models import Project, Test

logger = logging.getLogger(__name__)

def index(request):
    last_tests_by_project = []
    # Only tests executed in last 30 days
    tests = Test.objects.filter(
        started_at__gt=datetime.now() - timedelta(days=30)
    ).values('project_id').annotate(
        latest_time=Max('started_at')
    )
    for test in tests:
        project_id = test.project_id
        t = Test.objects.filter(
            project_id=project_id, started_at=test.latest_time
        ).values(
            'project__name', 'name', 'id',
            'project_id', 'parameters', 'started_at'
        )
        last_tests_by_project.append(t.first())
    last_tests = Test.objects.filter(project__enabled=True).values(
        'project__name', 'project_id', 'name', 'id',
        'started_at').order_by('-started_at')[:10]
    tests = dashboard_compare_tests_list(last_tests)
    tests_by_project = dashboard_compare_tests_list(last_tests_by_project)
    return render(
        request, 'jltc/dashboard.html', {
            'last_tests': tests,
            'last_tests_by_project': tests_by_project,
        }
    )


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
            'name':
            t['project__name'],
            'name':
            t['name'],
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
