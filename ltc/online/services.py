"""
Throttled refresh of online (live) test data.

TestOnlineData.update() re-reads the JMeter result CSV and writes to the
database — far too heavy to run on every poll of the API. Guard it with a
short cache-based cooldown so concurrent/frequent polls reuse fresh data.
"""
import logging

from django.core.cache import cache

from ltc.online.models import TestOnlineData

logger = logging.getLogger('django')

REFRESH_COOLDOWN_SECONDS = 5


def refresh_online_data(test):
    """Run TestOnlineData.update(test) at most once per cooldown window."""
    cache_key = f'online-refresh-{test.id}'
    if not cache.add(cache_key, True, REFRESH_COOLDOWN_SECONDS):
        return False
    TestOnlineData.update(test)
    return True
