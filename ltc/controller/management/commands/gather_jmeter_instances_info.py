import logging
import paramiko
from django.core.management.base import BaseCommand

from ltc.controller.models import SSHKey, JmeterServer, JmeterInstanceStatistic


logger = logging.getLogger("django")


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Connect and gather JAVA metrics from jmeter remote instances
        for jmeter_server in JmeterServer.objects.all():
            process_data = {}
            # Estimate number of threads at this moment
            if jmeter_server.test:
                threads_number = jmeter_server.threads
                process_data["threads_number"] = threads_number
            logger.info("threads_number: {};".format(threads_number))
            ssh_key = SSHKey.objects.get(default=True).path
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                jmeter_server.loadgenerator.hostname,
                username="root",
                key_filename=ssh_key,
            )
            cmd1 = "jstat -gc {}".format(jmeter_server.pid)
            stdin, stdout, stderr = ssh.exec_command(cmd1)
            i = 0

            header = str(stdout.readline()).split()
            data = str(stdout.readline()).split()
            if not (data):
                logger.error("No data in jstat -gc")
                continue
            for h in header:
                process_data[h] = data[i]
                i += 1
            # Need to sum this to get summary heap allocation:
            # S0U: Survivor space 0 utilization (kB).
            # S1U: Survivor space 1 utilization (kB).
            # EU: Eden space utilization (kB).
            # OU: Old space utilization (kB).
            JmeterInstanceStatistic(
                project_id=jmeter_server.test.project, data=process_data
            ).save()
            ssh.close()
