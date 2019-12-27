import os
import logging
import json
from django.conf import settings
from django.core.management.base import BaseCommand
from jltc.models import Test, TestFile, Project
from controller.views import generate_data
from argparse import ArgumentTypeError
logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def add_arguments(self, parser):
        # parser.add_argument(
        #     'jmeter_path', type=str,
        #     help='JMeter distr path'
        # )

        parser.add_argument(
            'testplan', type=str,
            help='testplan'
        )

        parser.add_argument(
            'result_file', type=str,
            help='Result File path'
        )

        parser.add_argument(
            'project', type=str,
            help='Result File path'
        )

        parser.add_argument(
            'threads', type=str,
            help='Result File path'
        )

        parser.add_argument(
            'thread_size', type=str,
            help='Result File path'
        )


    def handle(self, *args, **kwargs):
        test = Test()
        if 'project' in kwargs:
            project = Project.objects.get_or_create(name=kwargs['project'])
            test.project = project
        if 'threads' in kwargs:
            test.threads = int(kwargs['threads'])

        test.status = Test.CREATED
        test.save()
        TestFile(
            test=test,
            file_type=TestFile.TESTPLAN_FILE,
            path=kwargs['testplan']
        ).save()
        TestFile(
            test=test,
            file_type=TestFile.MAIN_RESULT_CSV_FILE,
            path=kwargs['result_file']
        ).save()
        test.prepare_test_plan()
        test.find_loadgenerators()