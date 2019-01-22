import logging
import math
import os
import random
import re
import subprocess
import threading
import time

import paramiko
from django.db.models import Avg, Count, FloatField
from django.db.models.expressions import F, RawSQL
from django.http import JsonResponse
from django.shortcuts import render

from administrator.models import SSHKey
from analyzer.models import Project
from controller.models import (ActivityLog, JmeterInstance,
                               JmeterInstanceStatistic, LoadGenerator,
                               TestRunning)
from controller.views.controller_views import prepare_test_plan

logger = logging.getLogger(__name__)


def get_avg_thread_malloc_for_project(project_id, threads_num):
    data = JmeterInstanceStatistic.objects.filter(project_id=project_id, data__contains=[{'threads_number': threads_num}]). \
        annotate(mem_alloc_for_thread=(RawSQL("((data->>%s)::numeric)", ('S0U',)) + RawSQL("((data->>%s)::numeric)", ('S1U',)) + RawSQL("((data->>%s)::numeric)", ('EU',)) + RawSQL("((data->>%s)::numeric)", ('OU',)))/1024/RawSQL("((data->>%s)::numeric)", ('threads_number',))). \
        aggregate(avg_mem_alloc_for_thread=Avg(
            F('mem_alloc_for_thread'), output_field=FloatField()))
    logger.debug("test_jmeter_instances_info: {}".format(str(data)))
    v = data['avg_mem_alloc_for_thread']
    logger.debug("Estimated MB per thread: {}".format(str(v)))
    if v is None:
        v = 10
    return v


def get_load_generators_data(request):
    load_generators_data = list(
        LoadGenerator.objects.annotate(jmeter_instances_count=Count(
            'jmeterinstance__id')).filter(active=True).values(
                'id',
                'hostname',
                'num_cpu',
                'memory',
                'memory_free',
                'la_1',
                'la_5',
                'la_15',
                'jmeter_instances_count',
                'reason',
                'status', ))
    return JsonResponse(load_generators_data, safe=False)


def get_load_generator_data(request, load_generator_id):
    load_generator = LoadGenerator.objects.get(id=load_generator_id)
    jmeter_instances = JmeterInstance.objects.annotate(
        project_name=F('project__project_name')).filter(
            load_generator_id=load_generator_id).values(
                'pid', 'port', 'jmeter_dir', 'project_name', 'threads_number',
                'java_args')
    return render(request, 'load_generator_page.html', {
        'load_generator': load_generator,
        'jmeter_instances': jmeter_instances,
    })


def prepare_load_generators(project_name,
                            workspace,
                            jmeter_dir,
                            threads_num,
                            duration,
                            rampup=0,
                            mb_per_thread=0,
                            additional_args='',
                            testplan_file='',
                            jenkins_env={}):
    response = {}
    if not Project.objects.filter(project_name=project_name).exists():
        logger.info('Creating a new project: {}.'.format(project_name))
        p = Project(project_name=project_name)
        p.save()
        project_id = p.id
    else:
        p = Project.objects.get(project_name=project_name)
        project_id = p.id
    start_time = int(time.time() * 1000)
    logger.info('Adding running test instance to DB.')
    t = TestRunning(
        project_id=project_id,
        start_time=start_time,
        duration=duration,
        workspace=workspace,
        rampup=rampup,
        is_running=False,
        testplan_file_dest=os.path.join(workspace, testplan_file),
        result_file_dest=os.path.join(workspace, 'result.jtl'),
    )
    # Insert CSV writer listener to test plan
    new_testplan_file = prepare_test_plan(t.workspace,
                                          t.testplan_file_dest,
                                          t.result_file_dest,
                                          )
    if new_testplan_file:
        logger.info('New testplan {}.'.format(new_testplan_file))
        if project_name != 'TropicalIsland':
            t.testplan_file_dest = new_testplan_file
    if jenkins_env:
        logger.info('Setting test build path.')
        t.build_path = os.path.join(
            jenkins_env['JENKINS_HOME'],
            'jobs',
            jenkins_env['JOB_NAME'],
            jenkins_env['BUILD_NUMBER'],
        )
        t.build_number = jenkins_env['BUILD_NUMBER']
        t.display_name = jenkins_env['BUILD_DISPLAY_NAME']
    t.save()
    test_running_id = t.id
    # get estimated required memory for one thread
    if mb_per_thread == 0:
        mb_per_thread = get_avg_thread_malloc_for_project(
            project_id, threads_num)
    logger.info(
        "Threads_num: {}; mb_per_thread: {}; project_name: {}; jmeter_dir: {}; duration: {}".
        format(threads_num, mb_per_thread, project_name, jmeter_dir, duration))
    matched_load_generators = []
    ready = False

    rmt = 0.0  # recommended_max_threads_per_one_jmeter_instance
    mem_multiplier = 2.0
    if mb_per_thread < 1.5:
        rmt = 500.0
        mem_multiplier = 2
    elif mb_per_thread >= 1.5 and mb_per_thread < 2:
        rmt = 400.0
    elif mb_per_thread >= 2 and mb_per_thread < 5:
        rmt = 300.0
    elif mb_per_thread >= 5 and mb_per_thread < 10:
        rmt = 200.0
    elif mb_per_thread >= 10:
        rmt = 100.0

    logger.info("Threads per jmeter instance: {};".format(rmt))
    logger.debug("ceil1: {};".format(float(threads_num) / rmt))
    logger.debug("ceil2: {};".format(math.ceil(float(threads_num) / rmt)))
    target_amount_jri = int(math.ceil(float(threads_num) / rmt))
    required_memory_for_jri = int(math.ceil(
        mb_per_thread * rmt * mem_multiplier))  # why 2 ? dunno
    required_memory_total = math.ceil(
        target_amount_jri * required_memory_for_jri * 1.2)
    logger.info('HEAP Xmx: {}'.format(required_memory_for_jri))
    logger.info("target_amount_jri: {}; required_memory_total: {}".format(
        target_amount_jri, required_memory_total))
    java_args = "-server -Xms{}m -Xmx{}m -Xss228k -XX:+DisableExplicitGC -XX:+CMSClassUnloadingEnabled -XX:+UseCMSInitiatingOccupancyOnly -XX:CMSInitiatingOccupancyFraction=70 -XX:+ScavengeBeforeFullGC -XX:+CMSScavengeBeforeRemark -XX:+UseConcMarkSweepGC -XX:+CMSParallelRemarkEnabled -Djava.net.preferIPv6Addresses=true -Djava.net.preferIPv4Stack=false".format(
        required_memory_for_jri, required_memory_for_jri)

    # java_args = "-server -Xms{}m -Xmx{}m  -Xss228k -XX:+UseConcMarkSweepGC -XX:+CMSParallelRemarkEnabled -XX:+DisableExplicitGC -XX:+CMSClassUnloadingEnabled -XX:+AggressiveOpts -Djava.net.preferIPv6Addresses=true -Djava.net.preferIPv4Stack=false".format(
    #    required_memory_for_jri, required_memory_for_jri)
    # update_load_generators_info()
    # java_args = "-server -Xms{}m -Xmx{}m -XX:+UseG1GC -XX:MaxGCPauseMillis=100 -XX:G1ReservePercent=20 -Djava.net.preferIPv6Addresses=true".format(
    #    required_memory_for_jri, required_memory_for_jri)
    load_generators_info = list(
        LoadGenerator.objects.filter(active=True).values())
    load_generators_count = LoadGenerator.objects.filter(active=True).count()

    running_test_jris = []
    overall_hosts_amount_jri = 0

    threads_per_host = int(float(threads_num) / target_amount_jri)

    if not ready:
        logger.info(
            "Did not a single load generator. Trying to find a combination.")
        t_hosts = {}
        # Try to find a combination of load generators:
        for generator in load_generators_info:
            hostname = generator['hostname']
            num_cpu = float(generator['num_cpu'])
            memory_free = float(generator['memory_free'])
            memory = float(generator['memory'])
            la_1 = float(generator['la_1'])
            la_5 = float(generator['la_5'])
            la_15 = float(generator['la_15'])
            status = generator['status']
            p = memory_free / (required_memory_for_jri * 1.2)
            t_hosts[hostname] = math.ceil(memory_free /
                                          (required_memory_for_jri * 1.2))
        t_sorted_hosts = sorted(t_hosts, key=t_hosts.get, reverse=True)

        # Try to spread them equally on load generators
        estimated_jris_for_host = int(
            math.ceil(float(target_amount_jri) / float(load_generators_count)))
        logger.debug(
            "estimated_jris_for_host: {};".format(estimated_jris_for_host))
        for h in t_sorted_hosts:
            possible_jris_on_host = t_hosts[h]
            if possible_jris_on_host > estimated_jris_for_host:
                possible_jris_on_host = estimated_jris_for_host
            if overall_hosts_amount_jri + possible_jris_on_host > target_amount_jri:
                possible_jris_on_host = target_amount_jri - overall_hosts_amount_jri
            logger.debug("h: {}; possible_jris_on_host: {};".format(
                h, possible_jris_on_host))
            matched_load_generators.append({
                'hostname':
                h,
                'possible_jris_on_host':
                int(possible_jris_on_host)
            })
            overall_hosts_amount_jri += possible_jris_on_host
            logger.debug("overall_hosts_amount_jri: {};".format(
                overall_hosts_amount_jri))
            if overall_hosts_amount_jri >= target_amount_jri:
                ready = True
                break
    if not ready and overall_hosts_amount_jri < target_amount_jri:
        logger.debug(
            "################CREATING NEW LOAD GENERATOR###################")
        n = target_amount_jri - overall_hosts_amount_jri
        required_memory_for_new_generators = n * required_memory_for_jri * 1.3
        logger.debug("required_memory_for_new_generators: {};".format(
            required_memory_for_new_generators))
        num_of_new_load_generators = int(math.ceil(
            float(required_memory_for_new_generators) / 4096))
        logger.debug("num_of_new_load_generators: {};".format(
            num_of_new_load_generators))
        # Create new load generator server if current are not enough
        # for i in xrange(num_of_new_load_generators):
        # for i in xrange(1):
        #    env.host_string = 'generator3.loadtest'
        #    env.game = 'loadtest'
        #    env.task = 'loadgenerator_create'
        #    env.logger = logger
        #    env.ig_execute = ig_execute
        #    loadgenerator_create(4, 4096)
        # prepare_load_generators(project_name, workspace, jmeter_dir,
        #                        threads_num, duration, rampup, mb_per_thread)
    logger.debug(
        "matched_load_generators: {};".format(str(matched_load_generators)))
    data_pool_index = 0
    start_jri_threads = []
    if ready:
        for load_generator in matched_load_generators:
            thread = threading.Thread(
                target=start_jris_on_load_generator,
                args=(
                    load_generator,
                    threads_per_host,
                    test_running_id,
                    project_id,
                    jmeter_dir,
                    java_args,
                    data_pool_index,
                    running_test_jris,
                    additional_args))
            # Increment data pool index by number of jris on started thread
            data_pool_index += load_generator['possible_jris_on_host']
            thread.start()
            start_jri_threads.append(thread)
        for thread in start_jri_threads:
            thread.join()

        t.jmeter_remote_instances = running_test_jris
        t.is_running = True
        t.save()
        final_str = ""
        jmeter_instances = JmeterInstance.objects.annotate(
            hostname=F('load_generator__hostname')).filter(
                test_running_id=test_running_id).values('hostname', 'port')
        for jmeter_instance in jmeter_instances:
            hostname = jmeter_instance['hostname']
            port = jmeter_instance['port']
            final_str += "{}:{},".format(hostname, port)
        final_str = final_str[:-1]
        response = {
            'testplan': t.testplan_file_dest,
            "remote_hosts_string": final_str,
            "threads_per_host": threads_per_host
        }
    return response


def start_jris_on_load_generator(
        load_generator, threads_per_host, test_running_id, project_id,
        jmeter_dir, java_args, data_pool_index, running_test_jris, additional_args):
    logger.debug("Initial data pool index for load generator: {}".format(
        data_pool_index))
    hostname = load_generator['hostname']
    load_generator_id = LoadGenerator.objects.get(hostname=hostname).id
    possible_jris_on_host = load_generator['possible_jris_on_host']
    ssh_key = SSHKey.objects.get(default=True).path
    logger.info("Uploading jmeter to remote host: {}".format(hostname))
    # TODO: return to /tmp
    p = subprocess.Popen(
        [
            "rsync", "-avH", jmeter_dir, "-e", "ssh", "-i", ssh_key,
            "root@{}:/tmp/".format(hostname), "--delete"
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, username="root", key_filename=ssh_key)
    # create an array of used ports
    cmd1 = 'netstat -tulpn | grep LISTEN'
    stdin, stdout, stderr = ssh.exec_command(cmd1)
    used_ports = []
    netstat_output = str(stdout.readlines())
    ports = re.findall('\d+\.\d+\.\d+\.\d+\:(\d+)', netstat_output)
    ports_ipv6 = re.findall('\:\:\:(\d+)', netstat_output)
    p.wait()
    for port in ports:
        used_ports.append(int(port))
    for port in ports_ipv6:
        used_ports.append(int(port))
    ssh.close()
    # Starting Jmeter remote instances on free port
    for i in range(1, possible_jris_on_host + 1):
        port = int(random.randint(10000, 20000))
        while port in used_ports:
            port = int(random.randint(10000, 20000))
        logger.info(port)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, username="root", key_filename=ssh_key)
        logger.info(
            'Starting jmeter instance on remote host: {}'.format(hostname))
        data_pool_index += 1
        run_jmeter_server_cmd = 'nohup java {0} -Duser.dir={5}/bin/ -jar "{1}/bin/ApacheJMeter.jar" -Jserver.rmi.ssl.disable=true "-Djava.rmi.server.hostname={2}" -Dserver_port={3} -s -j jmeter-server.log -Jpoll={4} {6} > /dev/null 2>&1 '.\
            format(java_args, jmeter_dir, hostname, str(port), str(
                data_pool_index), jmeter_dir, additional_args)
        logger.info('nohup java {0} -jar "{1}/bin/ApacheJMeter.jar" -Jserver.rmi.ssl.disable=true "-Djava.rmi.server.hostname={2}" -Duser.dir={5}/bin/ -Dserver_port={3} -s -Jpoll={4} {6} > /dev/null 2>&1 '.
                    format(java_args, jmeter_dir, hostname, str(port), str(data_pool_index), jmeter_dir, additional_args))
        command = 'echo $$; exec ' + run_jmeter_server_cmd
        cmds = ['cd {0}/bin/'.format(jmeter_dir), command]
        stdin, stdout, stderr = ssh.exec_command(' ; '.join(cmds))
        pid = int(stdout.readline())
        running_test_jris.append({'hostname': hostname, 'pid': pid})
        ActivityLog(action="start_jmeter_instance", load_generator_id=load_generator_id, data={
                    "pid": pid, "port": port, "java_args": java_args}).save()
        jmeter_instance = JmeterInstance(
            test_running_id=test_running_id,
            load_generator_id=load_generator_id,
            pid=pid,
            port=port,
            jmeter_dir=jmeter_dir,
            project_id=project_id,
            threads_number=threads_per_host,
            java_args=java_args, )

        jmeter_instance.save()
        logger.info(
            'New jmeter instance was added to database, pid: {}, port: {}'.
            format(pid, port))
        ssh.close()


def stop_jmeter_instance(jmeter_instance):
    hostname = jmeter_instance['load_generator__hostname']
    load_generator_id = jmeter_instance['load_generator_id']
    pid = jmeter_instance['pid']
    jmeter_dir = jmeter_instance['jmeter_dir']
    ssh_key = SSHKey.objects.get(default=True).path
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, username="root", key_filename=ssh_key)
    logger.info('Killing remote Jmeter instance. hostname: {}; pid: {}'.format(
        hostname, pid))
    command = 'kill -TERM -P {0}'.format(str(pid))
    stdin, stdout, stderr = ssh.exec_command(command)
    check_pattern = re.compile('/tmp/jmeter')
    if check_pattern.match(jmeter_dir) is not None:
        logger.info(
            'Removing remote Jmeter instance directory: {} from remote host: {}'.
            format(jmeter_dir, hostname))
        cmds = ['rm -rf {}'.format(jmeter_dir)]
        stdin, stdout, stderr = ssh.exec_command(' ; '.join(cmds))
    JmeterInstance.objects.filter(
        load_generator_id=load_generator_id, pid=pid).delete()
    ActivityLog(action="stop_jmeter_instance",
                load_generator_id=load_generator_id, data={"pid": pid}).save()
    ssh.close()


def gather_error_data(test, load_generator):
    workspace = test['workspace']
    hostname = load_generator['load_generator__hostname']
    jmeter_dir = load_generator['jmeter_dir']
    errors_dir = jmeter_dir + '/bin/errors/'
    logger.info('Gathering errors data from: {}:{}'.format(
        hostname, jmeter_dir))
    ssh_key = SSHKey.objects.get(default=True).path
    p = subprocess.Popen(
        [
            "scp",  "-i", ssh_key, "-r",  "root@{}:{}".format(
                hostname, errors_dir), workspace
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE)
    p.wait()


def stop_test_for_project(project_name, gather_errors_data=False):
    tests_running = list(
        TestRunning.objects.filter(project__project_name=project_name)
        .values())
    for test in tests_running:
        test_running_id = test['id']
        jmeter_instances = JmeterInstance.objects.filter(
            test_running_id=test_running_id).values(
                'pid', 'load_generator__hostname', 'load_generator_id',
                'jmeter_dir')
        if gather_errors_data:
            load_generators = JmeterInstance.objects.filter(test_running_id=test_running_id).values(
                'jmeter_dir', 'load_generator__hostname').distinct()
            for load_generator in load_generators:
                gather_error_data(test, load_generator)
        for jmeter_instance in jmeter_instances:
            stop_jmeter_instance(jmeter_instance)
        logger.info('Delete running test: {}'.format(test_running_id))
        TestRunning.objects.get(id=test_running_id).delete()


def test_stop_all_tests():
    tests_running = list(TestRunning.objects.values())
    for test in tests_running:
        test_running_id = test['id']
        jmeter_instances = JmeterInstance.objects.filter(
            test_running_id=test_running_id).values(
                'pid', 'load_generator__hostname', 'load_generator_id',
                'jmeter_dir')
        for jmeter_instance in jmeter_instances:
            stop_jmeter_instance(jmeter_instance)
        logger.info('Delete running test: {}'.format(test_running_id))
        TestRunning.objects.get(id=test_running_id).delete()
