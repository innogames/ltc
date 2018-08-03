import fnmatch
import os
import re
import logging
import time
from sys import platform as _platform
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.db.models.expressions import F, RawSQL
from django.db.models import Avg, FloatField, Max, Min, Sum
from controller.models import TestRunning, TestRunningData
from administrator.models import Configuration
from analyzer.models import Project
from django.shortcuts import render
logger = logging.getLogger(__name__)
# Create your views here.

def tests_list(request):
    '''
    Returns list of running tests
    '''
    data = []

    # Check if running test is still exists and update it`s info if necessary
    for test_running in TestRunning.objects.all():
        result_file_dest = test_running.result_file_dest
        if not result_file_dest:
            workspace = test_running.workspace
            for root, dirs, files in os.walk(workspace):
                for f in fnmatch.filter(files, '*.jtl'):
                    result_file_dest = os.path.join(root, f)
                    test_running.result_file_dest = result_file_dest
                    test_running.save()
                for f in fnmatch.filter(files, '*.data'):
                    monitoring_file_dest = os.path.join(root, f)
                    test_running.monitoring_file_dest = monitoring_file_dest
                    test_running.save()
        if result_file_dest and not os.path.exists(result_file_dest):
            logger.debug("Remove running test from database: {}".format(
                result_file_dest))
            test_running =   TestRunning.objects.get(result_file_dest=result_file_dest)
            TestRunningData.objects.filter(
                test_running_id=test_running.id).delete()
            test_running.delete()

    if _platform == "linux" or _platform == "linux2":
        jenkins_path = Configuration.objects.get(name='jenkins_path').value
        MONITORING_DIRS = [jenkins_path + "jobs/", "/tmp/jltc/"]
    elif _platform == "win32":
        MONITORING_DIRS = ["C:\work\monitoring"]

    for MONITORING_DIR in MONITORING_DIRS:
        for root, dirs, files in os.walk(MONITORING_DIR):
            if "workspace" in root or "results" in root:
                for f in fnmatch.filter(files, '*.jtl'):
                    if os.stat(os.path.join(root, f)).st_size > 0:
                        result_file_dest = os.path.join(root, f)
                        if not TestRunning.objects.filter(
                                result_file_dest=result_file_dest).exists():
                            #project_name = 'work\reportdata\FoE'
                            # will be gone soon:
                            project_name = re.search('/([^/]+)/workspace', root).group(1)
                            p = Project.objects.get(project_name=project_name)
                            logger.debug(
                                "Adding new running test to database: {}")
                            t = TestRunning(
                                result_file_dest=result_file_dest,
                                #project_id=272,
                                project_id=p.id,
                                is_running=True,
                                start_time=int(
                                    time.time() * 1000)  # REMOVE IT SOON
                            )
                            t.save()
                            t_id = t.id
                        else:
                            t = TestRunning.objects.get(
                                result_file_dest=result_file_dest)
                            t_id = t.id
                        # delete old tests from list
    for test_running in TestRunning.objects.all():
        data.append({
            "id":
            test_running.id,
            "result_file_dest":
            result_file_dest,
            "project_name":
            Project.objects.get(
                id=test_running.project_id).project_name,
        })
    return JsonResponse(data, safe=False)


def online_test_success_rate(request, test_running_id):
    test_running = TestRunning.objects.get(id=test_running_id)
    if test_running == None:
        response = {
            "message": {
                "text": "Running test with this id does not exists",
                "type": "danger",
                "msg_params": {
                    "test_running_id": test_running_id
                }
            }
        }
        return JsonResponse(response, safe=False)
    else:
        data = TestRunningData.objects.filter(name='data_over_time', test_running_id=test_running_id). \
                annotate(errors=RawSQL("((data->>%s)::numeric)", ('errors',))). \
                annotate(count=RawSQL("((data->>%s)::numeric)", ('count',))). \
                aggregate(count_sum=Sum(F('count'), output_field=FloatField()),
                errors_sum=Sum(F('errors'), output_field=FloatField()))
        errors_percentage = round(data['errors_sum'] * 100 / data['count_sum'],
                                  1)
        response = [{
            "fail_%": errors_percentage,
            "success_%": 100 - errors_percentage
        }]
        return JsonResponse(response, safe=False)


def online_test_response_codes(request, test_running_id):
    test_running = TestRunning.objects.get(id=test_running_id)
    if test_running == None:
        response = {
            "message": {
                "text": "Running test with this id does not exists",
                "type": "danger",
                "msg_params": {
                    "test_running_id": test_running_id
                }
            }
        }
        return JsonResponse(response, safe=False)
    else:
        response = []
        test_response_codes = TestRunningData.objects.get(
            name='response_codes', test_running_id=test_running_id).data
        for k in test_response_codes:
            response.append({
               'response_code': k,
               'count': test_response_codes.get(k)['count'],
            })
        return JsonResponse(response, safe=False)


def online_test_aggregate(request, test_running_id):
    aggregate = get_test_running_aggregate(test_running_id)
    return render(request, 'online_aggregate_table.html', {
        'aggregate_table': aggregate,
    })


def get_test_running_aggregate(test_running_id):
    test_running = TestRunning.objects.get(id=test_running_id)
    if test_running == None:
        response = {
            "message": {
                "text": "Running test with this id does not exists",
                "type": "danger",
                "msg_params": {
                    "test_running_id": test_running_id
                }
            }
        }
        return JsonResponse(response, safe=False)
    else:
        test_running_aggregate = TestRunningData.objects.get(
            name='aggregate_table', test_running_id=test_running_id).data

        return test_running_aggregate


def online_test_rps(request, test_running_id):
    test_running = TestRunning.objects.get(id=test_running_id)
    if test_running == None:
        response = {
            "message": {
                "text": "Running test with this id does not exists",
                "type": "danger",
                "msg_params": {
                    "test_running_id": test_running_id
                }
            }
        }
        return JsonResponse(response, safe=False)
    else:
        data = list(TestRunningData.objects.filter(name='data_over_time', test_running_id=test_running_id). \
                annotate(count=RawSQL("((data->>%s)::numeric)", ('count',))).order_by('-id').values('count'))

        response = [{
            "rps": int(data[1]['count']/60),
        }]
    return JsonResponse(response, safe=False)


def online_test_rtot(request, test_running_id):
    test_running = TestRunning.objects.get(id=test_running_id)
    if test_running == None:
        response = {
            "message": {
                "text": "Running test with this id does not exists",
                "type": "danger",
                "msg_params": {
                    "test_running_id": test_running_id
                }
            }
        }
        return JsonResponse(response, safe=False)
    else:
        response = []
        test_running_data_over_time = list(
            TestRunningData.objects.filter(
                name='data_over_time', test_running_id=test_running_id).values(
                    'data'))
        for d in test_running_data_over_time:
            response.append({
                'time': d['data']['timestamp'][:19],
                'rps': d['data']['count'] / 60,
                'avg': d['data']['avg'],
                'errors': d['data']['errors'],
            })
        return JsonResponse(response, safe=False)


def update(request, test_running_id):
    test_running = TestRunning.objects.get(id=test_running_id)
    response = {}
    if test_running == None:
        response = {
            "message": {
                "text": "Running test with this id does not exists",
                "type": "danger",
                "msg_params": {
                    "test_running_id": test_running_id
                }
            }
        }
    else:
        test_running.update_data_frame()
        response = {
            "message": {
                "text": "Running test data was updated",
                "type": "success",
                "msg_params": {
                    "test_running_id": test_running_id
                }
            }
        }
    return JsonResponse(response, safe=False)


class OnlinePage(TemplateView):
    def get(self, request, **kwargs):
        return render(request, 'online_page.html', context=None)
