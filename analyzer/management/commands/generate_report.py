import os
import logging
from django.conf import settings
from django.core.management.base import BaseCommand
from jltc.models import Test, TestFile
from controller.views import generate_data
from argparse import ArgumentTypeError
logger = logging.getLogger(__name__)

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

    def handle(self, *args, **kwargs):
        if 'jenkins_build_path' in kwargs:
            test = Test()
            test.save()
            TestFile(
                test=test,
                file_type=TestFile.MAIN_RESULT_CSV_FILE,
                path=kwargs['csv_file_path']
            ).save()
            TestFile(
                test=test,
                file_type=TestFile.JENKINS_BUILD_XML,
                path=os.path.join(
                    kwargs['jenkins_build_path'],
                    'build.xml',
                )
            ).save()
            test.init(source='jenkins_build')

            test.status = Test.RUNNING
            test.analyze()
