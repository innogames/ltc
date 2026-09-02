import logging

from django.core.management.base import BaseCommand

from ltc.base.models import Test, Project

logger = logging.getLogger('django')

class Command(BaseCommand):

    def add_arguments(self, parser):

        parser.add_argument(
            '--test',
            type=int,
            help='Test id'
        )

        parser.add_argument(
            '--project',
            type=str,
            help='project id'
        )

        parser.add_argument(
            '--force',
            type=bool,
            help='force recreate'
        )


    def handle(self, *args, **kwargs):
        force = False
        if kwargs.get('force'):
            force = True
        if kwargs.get('test'):
            test = Test.objects.get(id=kwargs['test'])
            test.post_to_confluence()
        elif kwargs.get('project'):
            project = Project.objects.get(name=kwargs['project'])
            project.generate_confluence_report(force=force)
