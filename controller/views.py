import json
import os
import subprocess
import sys
import psutil
import time

import signal
from analyzer.models import Project
from django.http import JsonResponse
from django.shortcuts import render


from models import Proxy, TestRunning
from django.db.models import Sum, Avg, Max, Min, FloatField


def change_proxy_delay(request, proxy_id):
	if request.method == 'POST':
		delay = request.POST.get('delay', '0')
		p = Proxy.objects.get(id=proxy_id)
		p.delay = delay
		p.save()
		response = [{"message":"proxy`s delay was changed", "proxy_id":proxy_id,"delay":delay}]
	return JsonResponse(response , safe=False)


def stop_proxy(request, proxy_id):
	p = Proxy.objects.get(id=proxy_id)
	if p.pid != 0:
		proxy_process = psutil.Process(p.pid)
		proxy_process.terminate()
		p.started = False
		p.pid = 0
		p.save()
		proxy = Proxy.objects.filter(id=proxy_id).values()
		response = [{"message":"proxy was stopped", "proxy":list(proxy)[0]}]
	else:
		proxy = Proxy.objects.filter(id=proxy_id).values()
		response = [{"message":"proxy is already stopped", "proxy":list(proxy)[0]}]
	return JsonResponse(response , safe=False)


def start_proxy(request, proxy_id):
	p = Proxy.objects.get(id=proxy_id)
	if request.method == 'POST':
		port = request.POST.get('port', '0')
		destination = request.POST.get('destination','https://empty')
		delay = request.POST.get('delay','0')
		p.delay = delay
		p.port = port
		p.destination = destination
		p.started = True
		p.save()
	out = open('/tmp/proxy_output_'+str(proxy_id), 'w')

	env = dict(os.environ, **{'PYTHONUNBUFFERED':'1'})
	proxy_process = subprocess.Popen([sys.executable, 'proxy.py', str(p.port),
									  p.destination, str(p.id)],
									  cwd=os.path.dirname(os.path.realpath(__file__)) ,
						 			  stdout=out, stderr=out, env = env
									 )
	print "proxy pid:" + str(proxy_process.pid)
	p = Proxy.objects.get(id=proxy_id)
	p.pid = proxy_process.pid
	p.save()
	p = Proxy.objects.filter(id=proxy_id).values()
	response = [{"message":"proxy was started", "proxy":list(p)[0]}]
	print response
	return JsonResponse(response , safe=False)


def add_proxy(request):
	if request.method == 'POST':
		port = request.POST.get('port', '0')
		destination = request.POST.get('destination','https://empty')
		delay = request.POST.get('delay','0')
		p = Proxy(delay=delay,
				  port = port,
				  destination = destination,
				  started = False,
				  pid =0)
		p.save()
		new_id = p.id
		proxy = Proxy.objects.filter(id=new_id).values()
		response = [{"message":"proxy was started", "proxy":list(proxy)[0]}]
	return JsonResponse(response , safe=False)


def new_proxy_page(request):
	return render (request, "new_proxy_page.html")


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
	return render(request, 'controller_page.html',
				  {'projects_list': projects_list,
				   'running_tests_list':running_tests_list,
				   'proxies_list': list(proxies_list)})


def configure_test(request, project_id):
	project = Project.objects.values().get(id=project_id)
	jmeter_parameters = json.loads(json.dumps(project['jmeter_parameters'], indent=4, sort_keys=True))
	print jmeter_parameters
	return render(request, 'configure_test_page.html',
				  {'project': project,
				   'jmeter_parameters':jmeter_parameters,
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

		args = [java_exec, '-jar', jmeter_path,
				"-n", "-t", project.test_plan_destination, '-j', "C:\work\jltommeter.log",
				'-Jjmeter.save.saveservice.default_delimiter=,', ]
		jmeter_process = subprocess.Popen(args,executable=java_exec)
		pid = jmeter_process.pid
		start_time = int(time.time())
		t = TestRunning(
			pid=pid,
			start_time=start_time,
			result_file_path=result_file_path,
			display_name=display_name,
			project_id=project_id
		)
		t.save()
		test_id = t.id;

	project = Project.objects.filter(id=project_id).values()
	response = [{"message":"test was started",
				 "test_id":test_id,
				 "pid":pid,
				 "project":list(project)[0]}]
	return JsonResponse(response , safe=False)


def stop_test(request, running_test_id):
	running_test = TestRunning.objects.get(id=running_test_id)
	response = []
	try:
		proxy_process = psutil.Process(running_test.pid)
		proxy_process.terminate()
		response = [{"message":"test was stopped",
					 "test_id":running_test_id,
					 "pid":running_test.pid
					}]
		running_test.delete()
	except psutil.NoSuchProcess:
		response = [{"message":"test does not exist",
					 "test_id":running_test_id
					 }]
		running_test.delete()
	return JsonResponse(response , safe=False)
