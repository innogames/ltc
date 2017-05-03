#
import json
import os
import subprocess
import sys
import psutil
import time
from sys import platform as _platform

if _platform == "linux" or _platform == "linux2":
    import resource

import signal
from analyzer.models import Project
from django.http import JsonResponse
from django.shortcuts import render

from models import Proxy, TestRunning, LoadGeneratorServer, JMeterTestPlanParameter, ScriptParameter
from django.db.models import Sum, Avg, Max, Min, FloatField


def setlimits():
    print "Setting resource limit in child (pid %d)" % os.getpid()
    if _platform == "linux" or _platform == "linux2":
        resource.setrlimit(resource.RLIMIT_NOFILE, (131072, 131072))


def change_proxy_delay(request, proxy_id):
    if request.method == 'POST':
        delay = request.POST.get('delay', '0')
        p = Proxy.objects.get(id=proxy_id)
        p.delay = delay
        p.save()
        response = [{
            "message": "proxy`s delay was changed",
            "proxy_id": proxy_id,
            "delay": delay
        }]
    return JsonResponse(response, safe=False)


def stop_proxy(request, proxy_id):
    p = Proxy.objects.get(id=proxy_id)
    if p.pid != 0:
        proxy_process = psutil.Process(p.pid)
        proxy_process.terminate()
        p.started = False
        p.pid = 0
        p.save()
        proxy = Proxy.objects.filter(id=proxy_id).values()
        response = [{"message": "proxy was stopped", "proxy": list(proxy)[0]}]
    else:
        proxy = Proxy.objects.filter(id=proxy_id).values()
        response = [{
            "message": "proxy is already stopped",
            "proxy": list(proxy)[0]
        }]
    return JsonResponse(response, safe=False)


def start_proxy(request, proxy_id):
    p = Proxy.objects.get(id=proxy_id)
    if request.method == 'POST':
        port = request.POST.get('port', '0')
        destination = request.POST.get('destination', 'https://empty')
        delay = request.POST.get('delay', '0')
        p.delay = delay
        p.port = port
        p.destination = destination
        p.started = True
        p.save()
    out = open('/tmp/proxy_output_' + str(proxy_id), 'w')
    proxy_script = "proxy.py"
    #if _platform == "linux" or _platform == "linux2":
    #	proxy_script = "proxy_linux.py"
    env = dict(os.environ, **{'PYTHONUNBUFFERED': '1'})
    proxy_process = subprocess.Popen(
        [sys.executable, proxy_script, str(p.port), p.destination, str(p.id)],
        cwd=os.path.dirname(os.path.realpath(__file__)),
        stdout=out,
        stderr=out,
        env=env,
        preexec_fn=setlimits)
    print "proxy pid:" + str(proxy_process.pid)
    p = Proxy.objects.get(id=proxy_id)
    p.pid = proxy_process.pid
    p.save()
    p = Proxy.objects.filter(id=proxy_id).values()
    response = [{"message": "proxy was started", "proxy": list(p)[0]}]
    print response
    return JsonResponse(response, safe=False)


def add_proxy(request):
    if request.method == 'POST':
        port = request.POST.get('port', '0')
        destination = request.POST.get('destination', 'https://empty')
        delay = request.POST.get('delay', '0')
        p = Proxy(
            delay=delay,
            port=port,
            destination=destination,
            started=False,
            pid=0)
        p.save()
        new_id = p.id
        proxy = Proxy.objects.filter(id=new_id).values()
        response = [{"message": "proxy was started", "proxy": list(proxy)[0]}]
    return JsonResponse(response, safe=False)


def new_proxy_page(request):
    return render(request, "new_proxy_page.html")


def new_jri_page(request, project_id):
    return render(request, "new_jri.html", {'project_id': project_id})


def new_jmeter_param_page(request, project_id):
    return render(request, "new_jmeter_param.html", {'project_id': project_id})


def new_script_param_page(request, project_id):
    return render(request, "new_script_param.html", {'project_id': project_id})


def jri_list(request, project_id):
    project = Project.objects.values().get(id=project_id)
    jris = json.loads(
        json.dumps(
            project['jmeter_remote_instances'], indent=4, sort_keys=True))
    if jris is None:
        jris = []
    return render(request, 'jri.html', {'jris': jris, 'project': project})


def jmeter_param_delete(request, project_id, param_id):
    project = Project.objects.values().get(id=project_id)
    jmeter_params = json.loads(
        json.dumps(project['jmeter_parameters'], indent=4, sort_keys=True))
    for i in xrange(len(jmeter_params)):
        if int(jmeter_params[i]['id']) == int(param_id):
            jmeter_params.pop(i)
            break
    project = Project.objects.get(id=project_id)
    project.jmeter_parameters = jmeter_params
    project.save()
    response = [{
        "message": "JMeter parameter was deleted",
        "project_id": project_id,
        "param_id": param_id
    }]
    return JsonResponse(response, safe=False)


def script_param_delete(request, project_id, param_id):
    project = Project.objects.values().get(id=project_id)
    script_params = json.loads(
        json.dumps(project['script_parameters'], indent=4, sort_keys=True))
    for i in xrange(len(script_params)):
        if int(script_params[i]['id']) == int(param_id):
            script_params.pop(i)
            break
    project = Project.objects.get(id=project_id)
    project.script_parameters = script_params
    project.save()
    response = [{
        "message": "Script parameter was deleted",
        "project_id": project_id,
        "param_id": param_id
    }]
    return JsonResponse(response, safe=False)


def jri_delete(request, project_id, jri_id):
    project = Project.objects.values().get(id=project_id)
    jris = json.loads(
        json.dumps(
            project['jmeter_remote_instances'], indent=4, sort_keys=True))
    for i in xrange(len(jris)):
        if int(jris[i]['id']) == int(jri_id):
            jris.pop(i)
            break
    project = Project.objects.get(id=project_id)
    project.jmeter_remote_instances = jris
    project.save()
    response = [{
        "message": "JRI was deleted",
        "project_id": project_id,
        "jri_id": jri_id
    }]
    return JsonResponse(response, safe=False)


def add_jmeter_param(request, project_id):
    project = Project.objects.values().get(id=project_id)
    response = []
    if request.method == 'POST':
        p_id = 0
        p_name = request.POST.get('name', 'name').strip()
        if not JMeterTestPlanParameter.objects.filter(p_name=p_name).exists():
            p = JMeterTestPlanParameter(p_name=p_name)
            p.save()
            p_id = p.id
        else:
            p = JMeterTestPlanParameter.objects.get(p_name=p_name)
            p_id = p.id

        value = request.POST.get('value', '1')
        jmeter_params = json.loads(
            json.dumps(project['jmeter_parameters'], indent=4, sort_keys=True))
        if jmeter_params is None:

            jmeter_params = list([{
                'id': p_id,
                'p_name': p_name,
                'value': value,
                'comment': ""
            }])
            response = [{
                "message": "JRI was added",
                'id': p_id,
                'p_name': p_name,
                'value': value,
                'comment': ""
            }]
        else:
            already_in_list = False
            for jmeter_param in jmeter_params:
                if jmeter_param.get('p_name') == p_name:
                    already_in_list = True
            if already_in_list:
                response = [{
                    "message":
                    "Jmeter parameter with the same "
                    "name is already exists",
                }]
            else:
                jmeter_params.append({
                    'id': p_id,
                    'p_name': p_name,
                    'value': value,
                    'comment': ""
                })
                response = [{
                    "message": "Jmeter parameter was added",
                    'id': p_id,
                    'p_name': p_name,
                    'value': value,
                    'comment': ""
                }]
        project = Project.objects.get(id=project_id)
        project.jmeter_parameters = jmeter_params
        project.save()
    return JsonResponse(response, safe=False)


def add_script_param(request, project_id):
    project = Project.objects.values().get(id=project_id)
    response = []
    if request.method == 'POST':
        p_id = 0
        p_name = request.POST.get('name', 'name').strip()
        if not ScriptParameter.objects.filter(p_name=p_name).exists():
            p = ScriptParameter(p_name=p_name)
            p.save()
            p_id = p.id
        else:
            p = ScriptParameter.objects.get(p_name=p_name)
            p_id = p.id

        value = request.POST.get('value', '1')
        script_params = json.loads(
            json.dumps(project['script_parameters'], indent=4, sort_keys=True))
        if script_params is None:

            script_params = list([{
                'id': p_id,
                'p_name': p_name,
                'value': value,
                'comment': ""
            }])
            response = [{
                "message": "Script parameter was added",
                'id': p_id,
                'p_name': p_name,
                'value': value,
                'comment': ""
            }]
        else:
            already_in_list = False
            for script_param in script_params:
                if script_param.get('p_name') == p_name:
                    already_in_list = True
            if already_in_list:
                response = [{
                    "message":
                    "Script parameter with the same "
                    "name is already exists",
                }]
            else:
                script_params.append({
                    'id': p_id,
                    'p_name': p_name,
                    'value': value,
                    'comment': ""
                })
                response = [{
                    "message": "Script parameter was added",
                    'id': p_id,
                    'p_name': p_name,
                    'value': value,
                    'comment': ""
                }]
        project = Project.objects.get(id=project_id)
        project.script_parameters = script_params
        project.save()
    return JsonResponse(response, safe=False)

def script_header(project_id):
    script_header = "#!/bin/bash\n"
    project = Project.objects.values().get(id=project_id)
    script_params = project['script_parameters']
    if script_params is None:
        script_params = []

    script_params_string = ""
    for script_param in script_params:
        script_params_string += "{0}={1}\n".format(
		script_param.get('p_name'),
		script_param.get('value'))
    script_header += script_params_string
    return script_header

def script_pre_configure(request, project_id):
    project = Project.objects.values().get(id=project_id)
    script_type = "pre"
    return render(request, 'script_config.html',
                  {'project': project,
                   'script_type': script_type,
				   'script_header': script_header(project_id)})


def script_post_configure(request, project_id):
    project = Project.objects.values().get(id=project_id)
    script_type = "post"
    return render(request, 'script_config.html',
                  {'project': project,
                   'script_type': script_type})


def script_pre_save(request, project_id):
    project = Project.objects.get(id=project_id)
    response = []
    if request.method == 'POST':
        script = request.POST.get('script', '')
        project.script_pre = script
        project.save()
        response = [{"message": "Pre-test script was changed"}]
    return JsonResponse(response, safe=False)


def script_post_save(request, project_id):
    project = Project.objects.get(id=project_id)
    response = []
    if request.method == 'POST':
        script = request.POST.get('script', '')
        project.script_post = script
        project.save()
        response = [{"message": "Post-test script was changed"}]
    return JsonResponse(response, safe=False)


def add_jri(request, project_id):
    project = Project.objects.values().get(id=project_id)
    response = []
    if request.method == 'POST':
        server_id = 0
        address = request.POST.get('address', '127.0.0.1')
        if not LoadGeneratorServer.objects.filter(address=address).exists():
            s = LoadGeneratorServer(address=address)
            s.save()
            server_id = s.id
        else:
            s = LoadGeneratorServer.objects.get(address=address)
            server_id = s.id
        count = request.POST.get('count', '1')
        jris = json.loads(
            json.dumps(
                project['jmeter_remote_instances'], indent=4, sort_keys=True))
        if jris is None:
            jris = list([{
                'id': server_id,
                'address': address,
                'count': count
            }])
            response = [{
                "message": "JRI was added",
                "id": server_id,
                "address": address,
                "count": count
            }]
        else:
            already_in_list = False
            for jri in jris:
                if jri.get('address') == address:
                    already_in_list = True
            if already_in_list:
                response = [{
                    "message": "JRI was already in list",
                }]
            else:

                jris.append({
                    'id': server_id,
                    'address': address,
                    'count': count
                })
                response = [{
                    "message": "JRI was added",
                    "id": server_id,
                    "address": address,
                    "count": count
                }]

        project = Project.objects.get(id=project_id)
        project.jmeter_remote_instances = jris
        project.save()
    return JsonResponse(response, safe=False)


def controller_page(request):
    projects_list = list(Project.objects.values())
    running_tests_list = TestRunning.objects.values()
    proxies_list = Proxy.objects.values()
    for proxy in proxies_list:
        if proxy["pid"] != 0:
            if not psutil.pid_exists(proxy["pid"]):
                p = Proxy.objects.get(id=proxy["id"])
                p.pid = 0
                p.started = False
                p.save()
    proxies_list = Proxy.objects.values()
    return render(request, 'controller_page.html', {
        'projects_list': projects_list,
        'running_tests_list': running_tests_list,
        'proxies_list': list(proxies_list)
    })


def configure_test(request, project_id):
    project = Project.objects.values().get(id=project_id)
    jmeter_parameters = json.loads(
        json.dumps(project['jmeter_parameters'], indent=4, sort_keys=True))
    jris = json.loads(
        json.dumps(
            project['jmeter_remote_instances'], indent=4, sort_keys=True))
    return render(request, 'configure_test_page.html', {
        'project': project,
        'jmeter_parameters': jmeter_parameters,
    })


def create_project_page(request):
    new_project = Project()
    new_project.save()
    return render(request, 'create_project_page.html',
           {
               'project': new_project,
           })


def create_project(request, project_id):
    project = Project.objects.get(id=project_id)
    response = []
    if request.method == 'POST':
        project_name = request.POST.get('project_name', '')
        jmeter_destination = request.POST.get('jmeter_destination', '')
        test_plan_destination = request.POST.get('test_plan_destination', '')
        project.jmeter_destination = jmeter_destination
        project.test_plan_destination = test_plan_destination
        project.project_name = project_name
        project.save()
    return JsonResponse(response, safe=False)


def delete_project(request, project_id):
    project = Project.objects.get(id=project_id)
    project.delete()
    response = [{
        "message": "project was deleted",
        "test_id": project_id
    }]
    return JsonResponse(response, safe=False)


def jmeter_params_list(request, project_id):
    project = Project.objects.values().get(id=project_id)
    jmeter_parameters = json.loads(
        json.dumps(project['jmeter_parameters'], indent=4, sort_keys=True))
    return render(request, 'jmeter_param.html', {
        'project': project,
        'jmeter_parameters': jmeter_parameters,
    })


def script_params_list(request, project_id):
    project = Project.objects.values().get(id=project_id)
    script_parameters = json.loads(
        json.dumps(project['script_parameters'], indent=4, sort_keys=True))
    return render(request, 'script_param.html', {
        'project': project,
        'script_parameters': script_parameters,
    })


def start_test(request, project_id):
    project = Project.objects.get(id=project_id)
    pid = 0
    start_time = 0
    result_file_path = ""
    display_name = ""
    test_id = 0
    if request.method == 'POST':
        jmeter_parameters = request.POST.get('jmeter_parameters', '{}')
        jmeter_destination = request.POST.get('jmeter_destination', '')
        test_plan_destination = request.POST.get('test_plan_destination', '{}')
        project.jmeter_destination = jmeter_destination
        project.jmeter_parameters = json.loads(jmeter_parameters)
        project.test_plan_destination = test_plan_destination
        project.save()
        java_exec = "C:\\Program Files\\Java\\jdk1.8.0_60\\bin\\java.exe"
        jmeter_path = project.jmeter_destination + "\ApacheJMeter.jar"

        args = [
            java_exec,
            '-jar',
            jmeter_path,
            "-n",
            "-t",
            project.test_plan_destination,
            '-j',
            "C:\work\jltommeter.log",
            '-Jjmeter.save.saveservice.default_delimiter=,',
        ]
        jmeter_process = subprocess.Popen(args, executable=java_exec)
        pid = jmeter_process.pid
        start_time = int(time.time())
        t = TestRunning(
            pid=pid,
            start_time=start_time,
            result_file_path=result_file_path,
            display_name=display_name,
            project_id=project_id)
        t.save()
        test_id = t.id

    project = Project.objects.filter(id=project_id).values()
    response = [{
        "message": "test was started",
        "test_id": test_id,
        "pid": pid,
        "project": list(project)[0]
    }]
    return JsonResponse(response, safe=False)


def stop_test(request, running_test_id):
    running_test = TestRunning.objects.get(id=running_test_id)
    response = []
    try:
        proxy_process = psutil.Process(running_test.pid)
        proxy_process.terminate()
        response = [{
            "message": "test was stopped",
            "test_id": running_test_id,
            "pid": running_test.pid
        }]
        running_test.delete()
    except psutil.NoSuchProcess:
        response = [{
            "message": "test does not exist",
            "test_id": running_test_id
        }]
        running_test.delete()
    return JsonResponse(response, safe=False)
