import logging
import re
import threading
import paramiko
#from adminapi.dataset import query
from django.core.management.base import BaseCommand
from administrator.models import SSHKey
from controller.models import LoadGenerator

logger = logging.getLogger(__name__)


def get_host_info(host, load_generators_info):
    hostname = host['hostname']
    logger.info('Checking loadgenerator {}'.format(hostname))
    ssh_key = SSHKey.objects.get(default=True).path
    logger.info("Use SSH key: {}".format(ssh_key))
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    logger.info('SSH to {}'.format(hostname))
    ssh.connect(hostname, username='root', key_filename=ssh_key)
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


class Command(BaseCommand):
    def handle(self, *args, **options):
        threads = []
        load_generators_info = []
        hosts = query(
            function='loadgenerator',
            state='online',
            servertype='vm',
        )

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
                logger.debug(
                    "Adding a new load generator: {}".format(hostname))
                new_lg = LoadGenerator(
                    hostname=hostname,
                    num_cpu=num_cpu,
                    memory=memory,
                    la_1=la_1,
                    la_5=la_5,
                    la_15=la_15,
                    status=status,
                    memory_free=memory_free,
                    reason=reason,
                    active=True, )
                new_lg.save()
            else:
                logger.debug(
                    "Updating a load generator data: {}".format(hostname))
                lg = LoadGenerator.objects.get(hostname=hostname)
                lg.num_cpu = num_cpu
                lg.memory = memory
                lg.memory_free = memory_free
                lg.la_1 = la_1
                lg.la_5 = la_5
                lg.la_15 = la_15
                lg.status = status
                lg.reason = reason
                lg.active = True
                lg.save()

        for generator in list(LoadGenerator.objects.values()):
            hostname = generator["hostname"]
            if hostname not in str(load_generators_info):
                logger.info(
                    'Remove loadgenerator from database: {}'.format(hostname))
                lg = LoadGenerator.objects.get(hostname=hostname)
                lg.active = False
                lg.save()
