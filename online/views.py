import fnmatch
import os
import re
import logging
import time
from sys import platform as _platform
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import TemplateView

from models import RunningTest, RunningTestsList
from controller.models import TestRunning
from analyzer.models import Project
from django.shortcuts import render
logger = logging.getLogger(__name__)
MONITORING_DIR = ""
# Create your views here.
if _platform == "linux" or _platform == "linux2":
    MONITORING_DIRS = ["/var/lib/jenkins/jobs/", "/tmp/jltc/"]
elif _platform == "win32":
    MONITORING_DIRS = ["C:\work\monitoring"]

rtl = RunningTestsList()


def tests_list(request):
    data = []
    running_tests_list = rtl.runningTestsList
    for MONITORING_DIR in MONITORING_DIRS:
        for root, dirs, files in os.walk(MONITORING_DIR):
            if "workspace" in root or "results" in root:
                for f in fnmatch.filter(files, '*.jtl'):
                    if os.stat(os.path.join(root, f)).st_size > 0:
                        result_file_dest = os.path.join(root, f)
                        if not TestRunning.objects.filter(result_file_dest=result_file_dest).exists():
                            project_name = re.search('/([^/]+)/workspace', root).group(1)
                            p = Project.objects.get(project_name=project_name)
                            logger.debug("Adding new running test to database: {}")
                            t = TestRunning(
                            result_file_dest=result_file_dest,
                            project_id=p.id,
                            is_running=True,
                            start_time=int(time.time() * 1000) # REMOVE IT SOON
                            )
                            t.save()
                            t_id = t.id
                        else:
                            t=TestRunning.objects.get(result_file_dest=result_file_dest)
                            t_id = t.id
                        logger.debug("Adding new running object: {}".format(t_id))
                        running_test = RunningTest(root, f)
                        running_tests_list.append(
                            [t_id, os.path.join(root, f), running_test])
                        # delete old tests from list
    for test_running in list(TestRunning.objects.values()):
        result_file_dest = test_running["result_file_dest"]
        if not os.path.exists(result_file_dest):
            logger.debug(
                "Remove running test from database: {}".format(result_file_dest))
            TestRunning.objects.filter(result_file_dest=result_file_dest).delete()
        else:
            data.append({
                "id": test_running["id"],
                "result_file_dest": result_file_dest,
                "project": Project.objects.get(id=test_running['project_id']),
            })
    rtl.runningTestsList = running_tests_list
    return JsonResponse(data, safe=False)


def online_test_success_rate(request, running_test_id):
    running_test = rtl.get_running_test(running_test_id)
    response = []
    if running_test == None:
        response.append({
            "error": "test does not exist",
            "running_test_id": running_test_id
        })
    else:
        data = running_test.successful_requests_percentage()
        response.append({"success_percentage": data})
    return JsonResponse(response, safe=False)
    #return JsonResponse(running_test.get_rtot_frame(), safe=False)


def online_test_response_codes(request, running_test_id):
    running_test = rtl.get_running_test(running_test_id)
    response = []
    if running_test == None:
        response.append({
            "error": "test does not exist",
            "running_test_id": running_test_id
        })
        return JsonResponse(response, safe=False)
    else:
        df = running_test.get_response_codes()
        return HttpResponse(df.to_json(orient='records'))


def online_test_aggregate(request, running_test_id):
    running_test = rtl.get_running_test(running_test_id)
    response = []
    if running_test == None:
        response.append({
            "error": "test does not exist",
            "running_test_id": running_test_id
        })
        return JsonResponse(response, safe=False)
    else:
        df = running_test.get_aggregate_frame()
        df = df.set_index('URL')
        return HttpResponse(df.to_html(classes='table'))


def online_test_rps(request, running_test_id):
    running_test = rtl.get_running_test(running_test_id)
    response = []
    if running_test == None:
        response.append({
            "error": "test does not exist",
            "running_test_id": running_test_id
        })
    else:
        data = running_test.last_minute_avg_rps()
        response.append({"rps": str(data)})
    return JsonResponse(response, safe=False)


def online_test_rtot(request, running_test_id):
    running_test = rtl.get_running_test(running_test_id)
    response = []
    if running_test == None:
        response.append({
            "error": "test does not exist",
            "running_test_id": running_test_id
        })
        return JsonResponse(response, safe=False)
    else:
        data = running_test.get_rtot_frame().to_json(orient='records')
        return HttpResponse(data)
        #return JsonResponse(running_test.get_rtot_frame(), safe=False)


def update(request, running_test_id):
    running_test = rtl.get_running_test(running_test_id)
    response = []
    if running_test == None:
        response.append({
            "error": "test does not exist",
            "running_test_id": running_test_id
        })
    else:
        running_test.update_data_frame()
        response.append({
            "message": "running test data was updated",
            "running_test_id": running_test_id
        })
    return JsonResponse(response, safe=False)


class OnlinePage(TemplateView):
    def get(self, request, **kwargs):
        return render(request, 'online_page.html', context=None)

