import logging
import threading

from django.core.management.base import BaseCommand

from adminapi.dataset import Query
from controller.models import LoadGenerator
from jltc.models import Configuration

logger = logging.getLogger(__name__)


def refresh(loadgenerator):
    """Update loadgenerator data

    Args:
        loadgenerator (LoadGenerator): loadgenerator hostname
    """

    loadgenerator.refresh()


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file_path', type=str,
            help='CSV with jmeter test results destination path'
        )
        parser.add_argument(
            '-jenkins_build_path', '--jenkins_build_path',
            type=str, help='Jenkins build destination path',
        )

    def handle(self, *args, **options):
        threads = []

        hosts = Query({
            'function': 'loadgenerator',
            'state': 'online',
            'servertype': 'vm',
        }, ['num_cpu', 'memory', 'hostname'])

        for host in hosts:
            print(host)
            loadgenerator, _ = LoadGenerator.objects.update_or_create(
                hostname=host['hostname'],
                defaults={
                    'num_cpu': host['num_cpu'],
                    'memory': host['memory'],
                },
            )
            t = threading.Thread(
                target=refresh, args=(
                    loadgenerator,
                )
            )
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
