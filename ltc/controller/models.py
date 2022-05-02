import datetime
import json
import random
import re
import logging
import os

from collections import OrderedDict, defaultdict
import subprocess
from django.db.models.fields import related

import pandas as pd
import paramiko
from django.contrib.postgres.fields import JSONField
from django.db import models
from pylab import np

# Create your models here.
from ltc.base.models import TestData

dateconv = np.vectorize(datetime.datetime.fromtimestamp)
logger = logging.getLogger('django')


class SSHKey(models.Model):
    path = models.TextField(default='')
    description = models.TextField(default='')
    default = models.BooleanField(default=True)

class ProjectGraphiteSettings(models.Model):
    project = models.ForeignKey(to='base.Project', on_delete=models.CASCADE)
    name = models.CharField(max_length=1000, default="")
    value = models.CharField(max_length=10000, default="")

    class Meta:
        db_table = 'project_graphite_settings'
        unique_together = (('project', 'value'))

class LoadGeneratorServer(models.Model):
    address = models.CharField(max_length=200, default="")
    ssh_key = models.ForeignKey(
        SSHKey, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'load_generator_server'


class LoadGenerator(models.Model):
    hostname = models.CharField(max_length=200, default='', unique=True)
    num_cpu = models.CharField(max_length=200, default='')
    memory = models.CharField(max_length=200, default='')
    memory_free = models.CharField(max_length=200, default='')
    la_1 = models.CharField(max_length=200, default='')
    la_5 = models.CharField(max_length=200, default='')
    la_15 = models.CharField(max_length=200, default='')
    active = models.BooleanField(default=True)

    def status(self):
        status = 'success'
        reason = 'ok'
        if float(self.memory_free) < float(self.memory) * 0.5:
            status = 'warning'
            reason = 'memory'
        elif float(self.memory_free) < float(self.memory) * 0.1:
            status = 'danger'
            reason = 'low memory'
        if float(self.la_5) > float(self.num_cpu) / 2:
            status = 'warning'
            reason = 'average load'
        elif float(self.la_5) > float(self.num_cpu):
            status = 'danger'
            reason = 'high load'
        return {'status': status, 'reason': reason}

    def refresh(self):
        """SSH to loadgenerator and gather system data
        """

        logger.info('Refresh loadgenerator data: %s', self.hostname)
        ssh_key = SSHKey.objects.filter(default=True).first()
        if not ssh_key:
            logger.info('SSH-key is not set')
            return
        ssh_key = ssh_key.path
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logger.info('ssh to %s', self.hostname)
        ssh.connect(self.hostname, username='root', key_filename=ssh_key)
        stdin, stdout, stderr = ssh.exec_command('cat /proc/meminfo')
        memory_free = str(
            int(re.search(
                'MemFree:\s+?(\d+)', str(stdout.readlines())
            ).group(1)) / 1024
        )
        stdin, stdout, stderr = ssh.exec_command('uptime')
        load_avg = re.search(
            'load average:\s+([0-9.]+?),\s+([0-9.]+?),\s+([0-9.]+)',
            str(stdout.readlines())
        )
        ssh.close()
        if load_avg:
            la_1 = load_avg.group(1)
            la_5 = load_avg.group(2)
            la_15 = load_avg.group(3)
        self.memory_free = memory_free
        self.la_1 = la_1
        self.la_5 = la_5
        self.la_15 = la_15
        self.active = True
        self.save()

    def start_jmeter_servers(
        self,
        jmeter_servers_per_generator,
        jmeter_servers_target_amount,
        test
    ):
        ssh_key = SSHKey.objects.get(default=True).path
        jmeter_path = f'/tmp/loadtest_{test.id}'
        logger.info(
            f'Rsyncing jmeter to remote host: {self.hostname}:{jmeter_path}'
        )
        p = subprocess.Popen(
            [
                "rsync", "-avH", f'{test.jmeter_path}/.' , "-e",
                f'ssh -i {ssh_key}',
                "root@{}:{}".format(self.hostname, jmeter_path),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE
        )
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.hostname, username='root', key_filename=ssh_key)
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
        for _ in range(0, jmeter_servers_per_generator):
            port = int(random.randint(10000, 20000))
            while port in used_ports:
                port = int(random.randint(10000, 20000))
            jmeter_server = JmeterServer(
                test=test,
                loadgenerator=self,
                port=port,
                jmeter_path=jmeter_path,
            )
            jmeter_server.start(test, jmeter_servers_target_amount)

    def distribute_testplan(self, test, test_plan):
        ssh_key = SSHKey.objects.get(default=True).path
        test_plan_path = os.path.dirname(os.path.abspath(test_plan.path))
        logger.info(
            f'Rsyncing test plan files {test_plan_path} '
            f'to remote host: {self.hostname}:{test.remote_temp_path}'
        )
        p = subprocess.Popen(
            [
                "rsync", "-aH", f'{test_plan_path}/.', "-e",
                f'ssh -i {ssh_key}',
                "root@{}:{}".format(self.hostname, test.remote_temp_path + '/bin')
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE
        )
        p.wait()

    def gather_errors_data(self, test):
        hostname = self.hostname
        errors_dir = test.remote_temp_path + '/bin/errors/'
        logger.info(f'Gathering errors data from: {hostname}:{errors_dir}')
        ssh_key = SSHKey.objects.get(default=True).path
        p = subprocess.Popen(
            [
                'scp', '-i', ssh_key, '-r',
                f'root@{hostname}:{errors_dir}',
                test.temp_path,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE
        )
        p.wait()

    def gather_logs(self, test):
        hostname = self.hostname
        logs_dir = test.remote_temp_path + '/bin/jmeter-server.log'
        logger.info(f'Gathering log data from: {hostname}:{logs_dir}')
        ssh_key = SSHKey.objects.get(default=True).path
        p = subprocess.Popen(
            [
                'scp', '-i', ssh_key, '-r',
                f'root@{hostname}:{logs_dir}',
                os.path.join(test.remote_temp_path, f'{self.hostname}.log')
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE
        )
        p.wait()

    def stop_jmeter_servers(self, test):
        jmeter_servers = JmeterServer.objects.filter(
            test=test, loadgenerator=self
        )
        if jmeter_servers.exists():
            ssh_key = SSHKey.objects.get(default=True).path
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.hostname, key_filename=ssh_key, username='root')
            for jmeter_server in jmeter_servers:
                logger.info(
                    f'Killing jmeter server on '
                    f'{self.hostname}:{jmeter_server.port} '
                    f'PID: {jmeter_server.pid}'
                )
                cmds = [f'kill -9 {jmeter_server.pid}']
                stdin, stdout, stderr = ssh.exec_command(' ; '.join(cmds))
                if not test.remote_temp_path:
                    continue
                logger.info(
                    f'Deleting tmp directory from {self.hostname}: '
                    f'{test.remote_temp_path}'
                )
                cmds = [f'rm -rf {test.remote_temp_path}']
                stdin, stdout, stderr = ssh.exec_command(' ; '.join(cmds))
            ssh.close()

    def __str__(self) -> str:
        return self.hostname

    class Meta:
        db_table = 'load_generator'


class JmeterServer(models.Model):
    test = models.ForeignKey(
        to='base.Test', on_delete=models.CASCADE
    )
    loadgenerator = models.ForeignKey(
        LoadGenerator, on_delete=models.CASCADE, related_name='jmeter_servers'
    )
    pid = models.IntegerField(default=0)
    port = models.IntegerField(default=0)
    jmeter_path = models.TextField(default='')
    threads = models.IntegerField(default=0)
    java_args = models.TextField(default='')
    local_args = models.TextField(default='')

    def java_args(self, memory):
        """Generate Java arg string for a new Jmeter server

        Args:
            memory (int): expected memory

        Returns:
            str: java args string
        """

        java_args = [
            '-server',
            '-Xms{memory}m',
            '-Xmx{memory}m',
            '-Xss228k',
            '-XX:+DisableExplicitGC',
            '-XX:+CMSClassUnloadingEnabled',
            '-XX:+UseCMSInitiatingOccupancyOnly',
            '-XX:CMSInitiatingOccupancyFraction=70',
            '-XX:+ScavengeBeforeFullGC',
            '-XX:+CMSScavengeBeforeRemark',
            '-XX:+UseConcMarkSweepGC',
            '-XX:+CMSParallelRemarkEnabled',
            '-Djava.net.preferIPv6Addresses=true',
            '-Djava.net.preferIPv4Stack=false'
        ]
        self.java_args = ' '.join(java_args).format(memory=memory)
        return self.java_args

    def start(self, test, jmeter_servers_target_amount):
        current_amount = JmeterServer.objects.filter(test=test).count()
        ssh_key = SSHKey.objects.get(default=True).path
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        hostname = self.loadgenerator.hostname
        local_args = ''
        for var in self.test.vars:
            if (
                any(v not in var for v in ['name', 'count', 'value']) or
                current_amount > int(var['count'])
            ):
                continue
            local_args += '-D{}={} '.format(
                var['name'], var['value']
            )
        for var in self.test.vars:
            if (
                any(v not in var for v in ['name', 'value']) or 'count' in var
            ):
                continue
            if var.get('distributed') is True:
                value = int(
                    float(var['value']) / jmeter_servers_target_amount
                )
                logger.info(
                    f'Estimated {var["name"]} per '
                    f'jmeter server: {value}'
                )
                local_args += ' -D{}={}'.format(
                    var['name'], value
                )
            elif var.get('script_files') is True:
                script_files = var.get('value')
                script_files_dst = os.path.join(
                    self.jmeter_path, os.path.basename(script_files)
                )
                if not script_files:
                    continue
                logger.info(
                    f'Uploading script files {script_files} to '
                    f'{self.loadgenerator.hostname}:{script_files_dst}'
                )
                p = subprocess.Popen(
                    [
                        "rsync", "-aH", f'{script_files}', "-e",
                        f'ssh -i {ssh_key}',
                        "root@{}:{}".format(
                            self.loadgenerator.hostname, script_files_dst
                        )
                    ],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE
                )
                p.wait()
                local_args += ' -D{}={}'.format(
                    var['name'], script_files_dst
                )
            else:
                local_args += ' -D{}={}'.format(
                    var['name'], var['value']
                )
        logger.info(
            f'Starting jmeter instance on : {hostname}:{self.port}'
        )
        ssh.connect(
            self.loadgenerator.hostname, username="root", key_filename=ssh_key
        )
        self.local_args = local_args
        start_jmeter_server_cmd = (
                f'nohup java {self.java_args(self.test.jmeter_malloc)} '
                f'-Duser.dir={self.jmeter_path}/bin/ -jar '
                f'"{self.jmeter_path}/bin/ApacheJMeter.jar" '
                f'-Jserver.rmi.ssl.disable=true '
                f'"-Djava.rmi.server.hostname={self.loadgenerator.hostname}" '
                f'-Dserver_port={self.port} -s -j jmeter-server.log '
                f'{self.local_args} > /dev/null 2>&1 '
            )
        logger.info(f'Using command: {start_jmeter_server_cmd}')
        command = 'echo $$; exec ' + start_jmeter_server_cmd
        cmds = ['cd {0}/bin/'.format(self.jmeter_path), command]
        stdin, stdout, stderr = ssh.exec_command(' ; '.join(cmds))
        pid = int(stdout.readline())
        self.pid = pid
        self.save()
        logger.info(
            f'New jmeter instance was added to database, pid: {self.pid},'
            f'port: {self.port}, test_id: {self.test.id}'
        )
        ssh.close()
        return True


class JmeterServerData(models.Model):
    project = models.ForeignKey(to='base.Project', on_delete=models.CASCADE)
    data = JSONField()

class ActivityLog(models.Model):
    date = models.DateTimeField(auto_now_add=True, blank=True)
    action = models.CharField(max_length=1000, default="")
    load_generator = models.ForeignKey(LoadGenerator, on_delete=models.CASCADE)
    data = JSONField()

    class Meta:
        db_table = 'activity_log'


class JmeterInstanceStatistic(models.Model):
    project = models.ForeignKey(to='base.Project', on_delete=models.CASCADE)
    data = JSONField()

    class Meta:
        db_table = 'jmeter_instance_statistic'


class JMeterTestPlanParameter(models.Model):
    p_name = models.CharField(max_length=200, default="")

    class Meta:
        db_table = 'jmeter_parameter'


class ScriptParameter(models.Model):
    p_name = models.CharField(max_length=200, default="")

    class Meta:
        db_table = 'script_parameter'
