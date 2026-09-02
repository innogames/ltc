import logging
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q

from ltc.base.models import Test

logger = logging.getLogger('django')


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        tests = Test.objects.exclude(status__in=[
                Test.FINISHED, Test.FAILED
            ]
        ).filter(
            Q(
                last_active__lte=datetime.now()-timedelta(hours=1)
            ) |
            Q(last_active__isnull=True)
        )
        for test in tests:
            logger.info(
                'Terminating stale test %s (last active: %s)',
                test.id, test.last_active
            )
            test.terminate()
