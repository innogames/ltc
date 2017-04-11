import fnmatch
import os
from sys import platform as _platform
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import TemplateView

from models import RunningTest, RunningTestsList
from django.shortcuts import render

MONITORING_DIR = ""
# Create your views here.
if _platform == "linux" or _platform == "linux2":
    MONITORING_DIR = "/var/lib/jenkins/jobs/"
elif _platform == "win32":
    MONITORING_DIR = "C:\work\monitoring"

rtl = RunningTestsList()

def tests_list(request):
    index = 0
    data = []
    running_tests_list = rtl.runningTestsList;
    for root, dirs, files in os.walk(MONITORING_DIR):
        if "workspace" in root:
            for f in fnmatch.filter(files, '*.jtl'):
                if os.stat(os.path.join(root, f)).st_size>0:
                    index += 1
                    if not any(os.path.join(root, f) in sublist
                               for sublist in running_tests_list):
                        if len(running_tests_list)>0:
                            # get the index of last element ^___^ and + 1
                            index = running_tests_list[-1][0] + 1
                        else:
                            index = 1
                        running_test = RunningTest(root, f)
                        running_tests_list.append([index,os.path.join(root, f),
                                                   running_test])
                        # delete old tests from list
    for running_test in running_tests_list:
        jmeter_results_file =  running_test[2].get_jmeter_results_file()
        if not os.path.exists(jmeter_results_file):
            rtl.remove(running_test)
        else:
            data.append({"id":running_test[0],"result_file_dist":jmeter_results_file});
    rtl.runningTestsList = running_tests_list
    return JsonResponse(data, safe=False)


def online_test_success_rate(request, running_test_id):
    running_test = rtl.get_running_test(running_test_id)
    response = []
    if running_test == None:
        response.append({"error":"test does not exist", "running_test_id":running_test_id});
    else:
        data = running_test.successful_requests_percentage()
        response.append({"success_percentage": data})
    return JsonResponse(response, safe=False)
    #return JsonResponse(running_test.get_rtot_frame(), safe=False)


def online_test_response_codes(request, running_test_id):
    running_test = rtl.get_running_test(running_test_id)
    response = []
    if running_test == None:
        response.append({"error":"test does not exist", "running_test_id":running_test_id});
        return JsonResponse(response, safe=False)
    else:
        df = running_test.get_response_codes()
        return HttpResponse(df.to_json(orient='records'))


def online_test_aggregate(request, running_test_id):
    running_test = rtl.get_running_test(running_test_id)
    response = []
    if running_test == None:
        response.append({"error":"test does not exist", "running_test_id":running_test_id});
        return JsonResponse(response, safe=False)
    else:
        df = running_test.get_aggregate_frame()
        df = df.set_index('URL')
        return HttpResponse(df.to_html(classes='table'))


def online_test_rps(request, running_test_id):
    running_test = rtl.get_running_test(running_test_id)
    response = []
    if running_test == None:
        response.append({"error":"test does not exist", "running_test_id":running_test_id});
    else:
        data = running_test.last_minute_avg_rps()
        response.append({"rps": str(data)})
    return JsonResponse(response, safe=False)


def online_test_rtot(request, running_test_id):
    running_test = rtl.get_running_test(running_test_id)
    response = []
    if running_test == None:
        response.append({"error":"test does not exist", "running_test_id":running_test_id});
        return JsonResponse(response, safe=False)
    else:
        data = running_test.get_rtot_frame().to_json(orient='records')
        return HttpResponse(data)
        #return JsonResponse(running_test.get_rtot_frame(), safe=False)




def update(request, running_test_id):
    running_test = rtl.get_running_test(running_test_id)
    response = []
    if running_test == None:
        response.append({"error":"test does not exist", "running_test_id":running_test_id});
    else:
        running_test.update_data_frame()
        response.append({"message":"running test data was updated", "running_test_id":running_test_id});
    return JsonResponse(response, safe=False)


class OnlinePage(TemplateView):
    def get(self, request, **kwargs):
        return render(request, 'online_page.html', context=None)