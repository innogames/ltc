''' ONLY FOR INSIDE INNNOGAMES '''
'''
import json
import os
import subprocess
import sys
import psutil
import time
import logging
import re
import string, threading
import kronos
import math
from subprocess import call
from sys import platform as _platform
from django.db.models.expressions import F, RawSQL
import select

import shutil

from controller.datagenerator import generate_data, parse_results_in_dir
from administrator.models import JMeterProfile, SSHKey

import paramiko
import tempfile

from analyzer.models import Project
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render

from controller.models import Proxy, TestRunning, LoadGeneratorServer, JMeterTestPlanParameter, ScriptParameter, LoadGenerator, JmeterInstance, JmeterInstanceStatistic
from django.db.models import Sum, Avg, Max, Min, Count, FloatField

from iggop.loadtest.fabfile import (
    _expand_hosts,
    #loadgenerator_create,
)
from fabric.api import env
from iggop.common.utils import (
    get_project, )
from adminapi.dataset import query
from adminapi.dataset.filters import Any, Regexp, Not
from collections import OrderedDict

logger = logging.getLogger(__name__)


def get_host_info(host, load_generators_info):
    logger.debug("Checking loadgenerator {}".format(host))
    ssh_key = SSHKey.objects.get(default=True).path
    logger.debug("Use SSH key: {}".format(ssh_key))
    hostname = host['hostname']
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, username="root", key_filename=ssh_key)
    cmd1 = 'cat /proc/meminfo'
    stdin, stdout, stderr = ssh.exec_command(cmd1)
    MemFree = str(
        int(re.search('MemFree:\s+?(\d+)', str(stdout.readlines())).group(1)) /
        1024)
    cmd2 = 'uptime'
    stdin, stdout, stderr = ssh.exec_command(cmd2)
    load_avg = re.search(
        'load average:\s+([0-9.]+?),\s+([0-9.]+?),\s+([0-9.]+)',
        str(stdout.readlines()))
    if load_avg:
        la_1 = load_avg.group(1)
        la_5 = load_avg.group(2)
        la_15 = load_avg.group(3)
    load_generators_info.append({
        'hostname': hostname,
        'num_cpu': host['num_cpu'],
        'memory': host['memory'],
        'memory_free': MemFree,
        'la_1': la_1,
        'la_5': la_5,
        'la_15': la_15,
    })
    ssh.close()


@kronos.register('* * * * *')
def update_load_generators_info():
    response = []
    threads = []
    load_generators_info = []
    env.game = 'loadtest'
    project = get_project(env.game),
    hosts = query(
        project=Any(project, 'admin'),
        function='loadgenerator',
        hostname=Not(Any('generator1.loadtest')))
    for host in hosts:
        t = threading.Thread(
            target=get_host_info, args=(
                host,
                load_generators_info, ))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    for generator in load_generators_info:
        hostname = generator['hostname']
        logger.debug(generator)
        num_cpu = float(generator['num_cpu'])
        memory = float(generator['memory'])
        memory_free = float(generator['memory_free'])
        la_1 = float(generator['la_1'])
        la_5 = float(generator['la_5'])
        la_15 = float(generator['la_15'])
        status = 'success'
        reason = 'ok'
        if memory_free < memory * 0.5:
            status = 'warning'
            reason = 'memory'
        elif memory_free < memory * 0.1:
            status = 'danger'
            reason = 'low memory'
        if la_5 > num_cpu / 2:
            status = 'warning'
            reason = 'average load'
        elif la_5 > num_cpu:
            status = 'danger'
            reason = 'high load'
        if not LoadGenerator.objects.filter(hostname=hostname).exists():
            logger.debug("Adding a new load generator: {}".format(hostname))
            new_lg = LoadGenerator(
                hostname=hostname,
                num_cpu=num_cpu,
                memory=memory,
                la_1=la_1,
                la_5=la_5,
                la_15=la_15,
                status=status,
                memory_free=memory_free,
                reason=reason)
            new_lg.save()
        else:
            logger.debug("Updating a load generator data: {}".format(hostname))
            lg = LoadGenerator.objects.get(hostname=hostname)
            lg.num_cpu = num_cpu
            lg.memory = memory
            lg.memory_free = memory_free
            lg.la_1 = la_1
            lg.la_5 = la_5
            lg.la_15 = la_15
            lg.status = status
            lg.reason = reason
            lg.save()

    for generator in list(LoadGenerator.objects.values()):
        hostname = generator["hostname"]
        if not hostname in str(load_generators_info):
            logger.debug(
                "Remove loadgenerator from database: {}".format(hostname))
            LoadGenerator.objects.filter(hostname=hostname).delete()


@kronos.register('*/5 * * * *')
def gather_jmeter_instances_info():
    #
    #Connect and gather JAVA metrics from jmeter remote instances
    #
    jmeter_instances = list(
        JmeterInstance.objects.annotate(hostname=F('load_generator__hostname'))
        .values('hostname', 'pid', 'project_id', 'threads_number',
                'test_running_id'))
    for jmeter_instance in jmeter_instances:
        current_time = int(time.time() * 1000)
        hostname = jmeter_instance['hostname']
        project_id = jmeter_instance['project_id']
        pid = jmeter_instance['pid']
        threads_number = jmeter_instance['threads_number']
        test_running_id = jmeter_instance['test_running_id']

        # Estimate number of threads at this moment
        test_running = TestRunning.objects.get(id=test_running_id)
        test_rampup = float(test_running.rampup) * 1000
        test_start_time = float(test_running.start_time)
        current_time = float(time.time() * 1000)
        if (test_start_time + test_rampup) > current_time:
            threads_number = int(
                threads_number *
                ((current_time - test_start_time) / test_rampup))

        logger.debug("threads_number: {};".format(threads_number))
        ssh_key = SSHKey.objects.get(default=True).path
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, username="root", key_filename=ssh_key)
        cmd1 = 'jstat -gc {}'.format(pid)
        stdin, stdout, stderr = ssh.exec_command(cmd1)
        i = 0
        process_data = {}
        header = str(stdout.readline()).split()
        data = str(stdout.readline()).split()
        for h in header:
            process_data[h] = data[i]
            i += 1
        logger.debug("process_data: {}".format(str(process_data)))
        process_data['threads_number'] = threads_number
        # Need to sum this to get summary heap allocation:
        # S0U: Survivor space 0 utilization (kB).
        # S1U: Survivor space 1 utilization (kB).
        # EU: Eden space utilization (kB).
        # OU: Old space utilization (kB).
        JmeterInstanceStatistic(
            project_id=project_id, data=process_data).save()
        ssh.close()
    return True


def get_avg_thread_malloc_for_project(project_id, threads_num):
    data = JmeterInstanceStatistic.objects.filter(project_id=project_id, data__contains=[{'threads_number': threads_num}]). \
        annotate(mem_alloc_for_thread=(RawSQL("((data->>%s)::numeric)", ('S0U',)) + RawSQL("((data->>%s)::numeric)", ('S1U',)) + RawSQL("((data->>%s)::numeric)", ('EU',)) + RawSQL("((data->>%s)::numeric)", ('OU',)))/1024/RawSQL("((data->>%s)::numeric)", ('threads_number',))). \
        aggregate(avg_mem_alloc_for_thread=Avg(F('mem_alloc_for_thread'), output_field=FloatField()))
    logger.debug("test_jmeter_instances_info: {}".format(str(data)))
    v = data['avg_mem_alloc_for_thread']
    logger.debug("Estimated MB per thread: {}".format(str(v)))
    if v is None:
        v = 10
    return v


def get_load_generators_data(request):
    load_generators_data = list(
        LoadGenerator.objects.annotate(jmeter_instances_count=Count(
            'jmeterinstance__id')).values(
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


def prepare_load_generators(project_name,
                            workspace,
                            jmeter_dir,
                            threads_num,
                            duration,
                            rampup=0,
                            mb_per_thread=0):

    if not Project.objects.filter(project_name=project_name).exists():
        logger.info("Creating a new project: {}".format(project_name))
        p = Project(project_name=project_name)
        p.save()
        project_id = p.id
    else:
        p = Project.objects.get(project_name=project_name)
        project_id = p.id
        
    for root, dirs, files in os.walk(workspace):
        for f in fnmatch.filter(files, '*.jtl'):
            result_file_dest = os.path.join(root, f)
        for f in fnmatch.filter(files, '*.data'):
            monitoring_file_dest = os.path.join(root, f)
                
    start_time = int(time.time() * 1000)
    t = TestRunning(
        project_id=project_id,
        start_time=start_time,
        duration=duration,
        workspace=workspace,
        rampup=rampup,
        result_file_dest=result_file_dest,
        monitoring_file_dest=monitoring_file_dest,
        is_running=False)
    t.save()
    test_running_id = t.id

    # get estimated required memory for one thread
    if mb_per_thread == 0:
        mb_per_thread = get_avg_thread_malloc_for_project(
            project_id, threads_num)
    logger.debug(
        "Threads_num: {}; mb_per_thread: {}; project_name: {}; jmeter_dir: {}; duration: {}".
        format(threads_num, mb_per_thread, project_name, jmeter_dir, duration))
    matched_load_generators = []
    ready = False

    rmt = 0.0  # recommended_max_threads_per_one_jmeter_instance
    if mb_per_thread < 2:
        rmt = 400.0
    elif mb_per_thread >= 2 and mb_per_thread < 5:
        rmt = 300.0
    elif mb_per_thread >= 5 and mb_per_thread < 10:
        rmt = 200.0
    elif mb_per_thread >= 10:
        rmt = 100.0

    logger.debug("rmt: {};".format(rmt))
    logger.debug("ceil1: {};".format(float(threads_num) / rmt))
    logger.debug("ceil2: {};".format(math.ceil(float(threads_num) / rmt)))
    target_amount_jri = int(math.ceil(float(threads_num) / rmt))
    required_memory_for_jri = int(math.ceil(
        mb_per_thread * rmt * 2))  # why 2 ? dunno
    required_memory_total = math.ceil(
        target_amount_jri * required_memory_for_jri * 1.3)  # why 1.3 ? dunno
    logger.info("target_amount_jri: {}; required_memory_total: {}".format(
        target_amount_jri, required_memory_total))
    java_args = "-server -Xms{}m -Xmx{}m -XX:+UseCMSInitiatingOccupancyOnly -XX:CMSInitiatingOccupancyFraction=70 -XX:+ScavengeBeforeFullGC -XX:+CMSScavengeBeforeRemark -XX:+UseConcMarkSweepGC -XX:+CMSParallelRemarkEnabled".format(
        required_memory_for_jri, required_memory_for_jri)
    #update_load_generators_info()
    load_generators_info = list(LoadGenerator.objects.values())
    load_generators_count = LoadGenerator.objects.count()
    
    running_test_jris = []
    overall_hosts_amount_jri = 0

    threads_per_host = int(float(threads_num) / target_amount_jri)

    if ready == False:
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
            reason = generator['reason']
            p = memory_free / (required_memory_for_jri * 1.3)
            if p > 10:
                p = 10
            t_hosts[hostname] = math.ceil(memory_free /
                                          (required_memory_for_jri * 1.3))
        t_sorted_hosts = sorted(t_hosts, key=t_hosts.get, reverse=True)
        
        # Try to spread them equally on load generators
        estimated_jris_for_host = int(math.ceil( float(target_amount_jri)/float(load_generators_count)))
        logger.debug("estimated_jris_for_host: {};".format(
                estimated_jris_for_host))
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
    if ready == False and overall_hosts_amount_jri < target_amount_jri:
        n = overall_hosts_amount_jri - target_amount_jri
        required_memory_for_new_generators = n * required_memory_for_jri * 1.3
        # Create new load generator server if current are not enough
        #loadgenerator_create(16, 16 * 1024)
        #prepare_load_generators(project_name, jmeter_dir, threads_num,
        #                    mb_per_thread, duration)
    logger.debug(
        "matched_load_generators: {};".format(str(matched_load_generators)))
    N = 0 # to separate data pools   
    for load_generator in matched_load_generators:
        hostname = load_generator['hostname']
        possible_jris_on_host = load_generator['possible_jris_on_host']
        ssh_key = SSHKey.objects.get(default=True).path
        logger.info("Uploading jmeter to remote host: {}".format(hostname))
        # TODO: return to /tmp
        p = subprocess.Popen(
            [
                "rsync", "-avH", jmeter_dir, "-e", "ssh", "-i", ssh_key,
                "{}:/tmp/".format(hostname), "--delete"
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
        ports = re.findall('\d+\.\d+\.\d+\.\d+\:(\d+)',
                           str(stdout.readlines()))
        p.wait()
        for port in ports:
            used_ports.append(int(port))
        ssh.close()
        for i in range(1, possible_jris_on_host + 1):
            port = 10000 + i
            if port not in used_ports:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(hostname, username="root", key_filename=ssh_key)
                logger.info('Starting jmeter instance on remote host: {}'.
                            format(hostname))
                cmds = [
                    'cd {0}/bin/'.format(jmeter_dir), 'DIRNAME=`dirname -- $0`'
                ]
                N += 1
                stdin, stdout, stderr = ssh.exec_command(' ; '.join(cmds))
                run_jmeter_server_cmd = 'nohup java {0} -jar "{1}/bin/ApacheJMeter.jar" "$@" "-Djava.rmi.server.hostname={2}" -Dserver_port={3} -s -Jpoll={4} > /dev/null 2>&1 '.\
                    format(java_args, jmeter_dir, hostname, str(port), str(N))
                logger.info('nohup java {0} -jar "{1}/bin/ApacheJMeter.jar" "$@" "-Djava.rmi.server.hostname={2}" -Dserver_port={3} -s -Jpoll={4} > /dev/null 2>&1 '.\
                    format(java_args, jmeter_dir, hostname, str(port), str(N)))
                command = 'echo $$; exec ' + run_jmeter_server_cmd
                stdin, stdout, stderr = ssh.exec_command(command)
                pid = int(stdout.readline())
                running_test_jris.append({'hostname': hostname, 'pid': pid})

                jmeter_instance = JmeterInstance(
                    test_running_id=test_running_id,
                    load_generator_id=LoadGenerator.objects.get(
                        hostname=hostname).id,
                    pid=pid,
                    port=port,
                    jmeter_dir=jmeter_dir,
                    project_id=project_id,
                    threads_number=threads_per_host,
                    # add project id, number of threads
                )

                jmeter_instance.save()
                logger.info(
                    'New jmeter instance was added to database, pid: {}, port: {}'.
                    format(pid, port))
                ssh.close()

    t.jmeter_remote_instances = running_test_jris
    t.is_running = True
    t.save()
    final_str = ""
    if ready:
        jmeter_instances = JmeterInstance.objects.annotate(
            hostname=F('load_generator__hostname')).filter(
                test_running_id=test_running_id).values('hostname', 'port')
        for jmeter_instance in jmeter_instances:
            hostname = jmeter_instance['hostname']
            port = jmeter_instance['port']
            final_str += "{}:{},".format(hostname, port)
    final_str = final_str[:-1]
    response = {
        "remote_hosts_string": final_str,
        "threads_per_host": threads_per_host
    }
    return response


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
    cmds = ['kill -9 {0}'.format(str(pid))]
    stdin, stdout, stderr = ssh.exec_command(' ; '.join(cmds))
    check_pattern = re.compile('/tmp/jmeter')
    if check_pattern.match(jmeter_dir) is not None:
        logger.info(
            'Removing remote Jmeter instance directory: {} from remote host: {}'.
            format(jmeter_dir, hostname))
        cmds = ['rm -rf {}'.format(jmeter_dir)]
        stdin, stdout, stderr = ssh.exec_command(' ; '.join(cmds))
    JmeterInstance.objects.filter(
        load_generator_id=load_generator_id, pid=pid).delete()
    ssh.close()


def stop_test_for_project(project_name):
    tests_running = list(
        TestRunning.objects.filter(project__project_name=project_name)
        .values())
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

'''