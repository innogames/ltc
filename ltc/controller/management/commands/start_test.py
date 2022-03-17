import os
import logging
import json
import signal
import time
from django.conf import settings
from django.core.management.base import BaseCommand
from ltc.base.models import Test, TestFile, Project
from ltc.controller.views import generate_data
from argparse import ArgumentTypeError
logger = logging.getLogger('django')

class Command(BaseCommand):

    def add_arguments(self, parser):

        parser.add_argument(
            '--jmeter_path',
            type=str,
            help='JMeter path'
        )

        parser.add_argument(
            '--temp_path',
            type=str,
            help='Temp path'
        )

        parser.add_argument(
            '--testplan',
            type=str,
            help='testplan'
        )

        parser.add_argument(
            '--project',
            type=str,
            help='Project'
        )

        parser.add_argument(
            '--threads',
            type=str,
            help='Amount of threads'
        )

        parser.add_argument(
            '--duration',
            type=int,
            help='Timeout'
        )

        parser.add_argument(
            '--thread_size',
            type=str,
            help='Thread size'
        )

        parser.add_argument(
            '--vars',
            type=str,
            help='Thread size'
        )

        parser.add_argument(
            '--nocleanup', action='store_true'
        )

    def handle(self, *args, **kwargs):

        test = Test()
        if 'project' in kwargs:
            project, _ = Project.objects.get_or_create(name=kwargs['project'])
            test.project = project
        if 'threads' in kwargs:
            test.threads = int(kwargs['threads'])
        if 'jmeter_path' in kwargs:
            test.jmeter_path = kwargs['jmeter_path']
        if 'temp_path' in kwargs:
            test.temp_path = kwargs['temp_path']
        if 'vars' in kwargs:
            vars = json.loads( kwargs['vars'])
            test.vars = vars
        if kwargs.get('duration'):
            test.duration = kwargs['duration']
        test.status = Test.CREATED
        test.save()
        test.prepare_test_plan(kwargs['testplan'])
        loadgenerators = {}
        jmeter_server_amount = 0
        if 'thread_size' in kwargs:
            loadgenerators, jmeter_server_amount = test.find_loadgenerators(
                int(kwargs['thread_size'])
            )
        test.prepare_jmeter()
        test.prepare_jmeter_servers(
            loadgenerators, jmeter_server_amount, kwargs['testplan']
        )
        # Sleep for a while to let the jmeter server start
        logger.info('Waiting 10 secs for jmeter servers to start')
        time.sleep(10)

        test.start()
        test.analyze()
        test.cleanup()
        test.project.generate_confluence_report()
