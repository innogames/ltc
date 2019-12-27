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
from jltc.models import Project
from controller.models import (
    ActivityLog, JmeterServer,
    LoadGenerator,
    TestRunning
)
from django.forms.models import model_to_dict
logger = logging.getLogger(__name__)

def get_load_generators_data(request):
    """
    Returns data for all load generators.
    """

    data = []
    for load_generator in LoadGenerator.objects.annotate(
            jmeter_servers_count=Count('jmeterserver_id')
        ).filter(
            active=True
        ):
            load_generator_data = model_to_dict(load_generator)
            load_generator_data['status'] = load_generator.status()
            load_generator_data[
                'jmeter_instances_count'
            ] = load_generator.jmeter_instances_count
            data.append(load_generator_data)
    return JsonResponse(data, safe=False)


def get_load_generator_data(request, load_generator_id):
    load_generator = LoadGenerator.objects.get(id=load_generator_id)
    jmeter_instances = JmeterServer.objects.annotate(
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
    t.save()
    # Insert CSV writer listener to test plan
    new_testplan_file = prepare_test_plan(
        t.workspace,
        t.testplan_file_dest,
        t.result_file_dest,
    )
    if new_testplan_file:
        logger.info('New testplan {}.'.format(new_testplan_file))
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
    test_running_id = t.id
    logger.info('New Test id: {}'.format(test_running_id))
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
    target_amount_jri = int(math.ceil(float(threads_num) / rmt))
    required_memory_for_jri = int(
        math.ceil(mb_per_thread * rmt * mem_multiplier))  # why 2 ? dunno
    required_memory_total = math.ceil(
        target_amount_jri * required_memory_for_jri * 1.2)
    logger.info('HEAP Xmx: {}'.format(required_memory_for_jri))
    logger.info('Target amount of Jmeter-servers: {};'
                'Required memory (total): {}'.format(target_amount_jri,
                                                     required_memory_total))
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
    current_amount_jri = 0
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
            if current_amount_jri + possible_jris_on_host > target_amount_jri:
                possible_jris_on_host = target_amount_jri - current_amount_jri
            logger.info("Host: {}; Possible JRIs on host: {};".format(
                h, possible_jris_on_host))
            matched_load_generators.append({
                'hostname':
                h,
                'possible_jris_on_host':
                int(possible_jris_on_host)
            })
            current_amount_jri += possible_jris_on_host
            logger.debug("current_amount_jri: {};".format(current_amount_jri))
            if current_amount_jri >= target_amount_jri:
                ready = True
                break
    if not ready and current_amount_jri < target_amount_jri:
        n = target_amount_jri - current_amount_jri
        logger.error('Current generators are not enough to start the test'
                     'Required JMeter instances: {}'.format(n))

    logger.debug("matched_load_generators: {};".format(
        str(matched_load_generators)))
    data_pool_index = 0
    start_jri_threads = []
    threads_per_jri = int(float(threads_num) / current_amount_jri)
    if ready:
        for load_generator in matched_load_generators:
            thread = threading.Thread(
                target=start_jris_on_load_generator,
                args=(load_generator, threads_per_jri, test_running_id,
                      project_id, jmeter_dir, java_args, data_pool_index,
                      running_test_jris, additional_args))
            # Increment data pool index by number of jris on started thread
            data_pool_index += load_generator['possible_jris_on_host']
            start_jri_threads.append(thread)
        for thread in start_jri_threads:
            thread.join()

        t.jmeter_remote_instances = running_test_jris
        t.is_running = True
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
            "threads_per_host": threads_per_jri,
            "threads_per_jri": threads_per_jri,
        }
        logger.info('Testplan destination: {}'.format(t.testplan_file_dest))
        logger.info('Saved Test id: {}'.format(t.id))
    return response


def start_jris_on_load_generator(load_generator, threads_per_jri,
                                 test_running_id, project_id, jmeter_dir,
                                 java_args, data_pool_index, running_test_jris,
                                 additional_args):
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
    p.wait()
    # Starting Jmeter remote instances on free port
    for i in range(1, possible_jris_on_host + 1):
        new_instance_data = {}
        t = 0
        pid = 0
        data_pool_index += 1
        while pid == 0:
            new_instance_data = start_jmeter_instance(
                    hostname,
                    java_args,
                    data_pool_index,
                    jmeter_dir,
                    additional_args,
            )
            pid = new_instance_data['pid']
            t = t + 1
            if t > 5:
                logger.error('Cannot start jmeter instances on {}'.format(
                        hostname
                ))
                break
        if pid > 0:
            running_test_jris.append({
                'hostname': hostname,
                'pid': new_instance_data['pid']
            })
            ActivityLog(
                action="start_jmeter_instance",
                load_generator_id=load_generator_id,
                data={
                    "pid": new_instance_data['pid'],
                    "port": new_instance_data['port'],
                    "java_args": java_args
                }
            ).save()
            jmeter_instance = JmeterInstance(
                test_running_id=test_running_id,
                load_generator_id=load_generator_id,
                pid=new_instance_data['pid'],
                port=new_instance_data['port'],
                jmeter_dir=jmeter_dir,
                project_id=project_id,
                threads_number=threads_per_jri,
                java_args=java_args,
            )
            jmeter_instance.save()
            logger.info(
                'New jmeter instance was added to database, '
                'pid: {}, port: {}, test_id: {}'.
                format(
                    new_instance_data['pid'],
                    new_instance_data['port'],
                    jmeter_instance.test_running_id
                )
            )

def start_jmeter_instance(
        hostname,
        java_args,
        data_pool_index,
        jmeter_dir,
        additional_args,
):
    ssh_key = SSHKey.objects.get(default=True).path
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, username="root", key_filename=ssh_key)
    logger.info('Starting jmeter instance on remote host: {}'.format(hostname))
    stdin, stdout, stderr = ssh.exec_command('netstat -tulpn | grep LISTEN')
    used_ports = []
    netstat_output = str(stdout.readlines())
    ports = re.findall('\d+\.\d+\.\d+\.\d+\:(\d+)', netstat_output)
    ports_ipv6 = re.findall('\:\:\:(\d+)', netstat_output)
    for p in ports:
        used_ports.append(int(p))
    for p in ports_ipv6:
        used_ports.append(int(p))
    port = int(random.randint(10000, 20000))
    while port in used_ports:
        port = int(random.randint(10000, 20000))
    logger.info('Selected port: {}'.format(port))
    run_jmeter_server_cmd = 'nohup java {0} -Duser.dir={5}/bin/ -jar "{1}/bin/ApacheJMeter.jar" -Jserver.rmi.ssl.disable=true "-Djava.rmi.server.hostname={2}" -Dserver_port={3} -s -j jmeter-server.log -Jpoll={4} {6} > /dev/null 2>&1 '.\
        format(java_args, jmeter_dir, hostname, str(port), str(
            data_pool_index), jmeter_dir, additional_args)
    logger.info(
        'nohup java {0} -jar "{1}/bin/ApacheJMeter.jar" -Jserver.rmi.ssl.disable=true "-Djava.rmi.server.hostname={2}" -Duser.dir={5}/bin/ -Dserver_port={3} -s -Jpoll={4} {6} > /dev/null 2>&1 '.
        format(java_args, jmeter_dir, hostname, str(port),
               str(data_pool_index), jmeter_dir, additional_args))
    command = 'echo $$; exec ' + run_jmeter_server_cmd
    cmds = ['cd {0}/bin/'.format(jmeter_dir), command]
    stdin, stdout, stderr = ssh.exec_command(' ; '.join(cmds))
    pid = stdout.readline().strip()
    stdin, stdout, stderr = ssh.exec_command('ls /proc/')
    ls_output = str(stdout.readlines())
    procs = re.findall('\d+', ls_output)
    ssh.close()
    if procs.count(pid) > 0 and used_ports.count(port) > 0:
        logger.info('{} process is using port: {}'.format(pid, port))
        return {'pid': pid, 'port': port}
    logger.info('Was a problem to start jmeter on {}:{}'.format(hostname, port)) 
    return {'pid': 0, 'port': port}


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
    #while os.path.exists('/proc/{}'.format(pid)):
    command = 'kill -9 {0}'.format(str(pid))
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
    ActivityLog(
        action="stop_jmeter_instance",
        load_generator_id=load_generator_id,
        data={
            "pid": pid
        }).save()
    ssh.close()


def gather_error_data(test, load_generator):
    workspace = test.workspace
    hostname = load_generator['load_generator__hostname']
    jmeter_dir = load_generator['jmeter_dir']
    errors_dir = jmeter_dir + '/bin/errors/'
    logger.info('Gathering errors data from: {}:{}'.format(
        hostname, jmeter_dir))
    ssh_key = SSHKey.objects.get(default=True).path
    p = subprocess.Popen(
        [
            "scp", "-i", ssh_key, "-r", "root@{}:{}".format(
                hostname, errors_dir), workspace
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE)
    p.wait()


def stop_test_for_project(project_name, gather_errors_data=False):
    """
    Stop test for jenkins project name

    :param project_name: jenkins project name
    :type project_name: str
    """

    logger.info('Stop test for project: {}'.format(project_name))
    project = Project.objects.get(project_name=project_name)
    tests_running = TestRunning.objects.filter(project=project)
    for test in tests_running:
        test_running_id = test.id
        logger.info('Stop test : {}'.format(test_running_id))
        jmeter_instances = JmeterServer.objects.filter(
            test_running_id=test_running_id).values(
                'pid', 'load_generator__hostname', 'load_generator_id',
                'jmeter_dir')
        if gather_errors_data:
            load_generators = JmeterServer.objects.filter(
                test_running_id=test_running_id).values(
                    'jmeter_dir', 'load_generator__hostname').distinct()
            for load_generator in load_generators:
                gather_error_data(test, load_generator)
        threads = []
        for jmeter_instance in jmeter_instances:
            thread = threading.Thread(
                target=stop_jmeter_instance,
                args=(jmeter_instance)
            )
            thread.start()
        for thread in threads:
            thread.join()
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
