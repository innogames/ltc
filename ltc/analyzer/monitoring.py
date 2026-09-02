"""
Server monitoring series for the Analyzer's Monitoring tab.

`ServerMonitoringData.data` rows are written per server per resolution
bucket with exactly these keys (see the historical writer, removed in
d5e80ac: `ltc/controller/views/data_generator.py`):

    timestamp                                   ISO-8601 string
    Memory_used, Memory_free,
    Memory_buff, Memory_cached                  memory counters
    Net_recv, Net_send, Disk_read, Disk_write   IO counters
    System_la1                                  1-minute load average
    CPU_user, CPU_system, CPU_iowait            percentages

CPU busy is the sum of the three CPU percentages — the same definition
`Test.get_test_metric('cpu_load')` uses. Memory-used percent is
Memory_used over the sum of all four memory counters, so buffers and
cache count as available (how `free`/`vmstat` report it).

This data only exists when the tested servers reported metrics during the
run, which is often not the case; everything here degrades to an empty
series rather than raising.
"""
import logging

from ltc.analyzer.models import ServerMonitoringData

logger = logging.getLogger('django')

CPU_KEYS = ('CPU_user', 'CPU_system', 'CPU_iowait')
MEMORY_KEYS = ('Memory_used', 'Memory_free', 'Memory_buff', 'Memory_cached')
LOAD_KEY = 'System_la1'


def _number(value):
    """JSONB values arrive as numbers, numeric strings, None or NaN."""
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None  # NaN != NaN


def _cpu_percent(row):
    present = [
        value for value in (_number(row.get(key)) for key in CPU_KEYS)
        if value is not None
    ]
    if not present:
        return None
    return round(sum(present), 2)


def _memory_percent(row):
    used = _number(row.get('Memory_used'))
    total = sum(
        value for value in (_number(row.get(key)) for key in MEMORY_KEYS)
        if value is not None
    )
    if used is None or not total:
        return None
    return round(used * 100 / total, 2)


def test_monitoring_data(test):
    """
    [{host, cpu: [percent], mem: [percent], la: str}] for one test, each
    series ordered by timestamp. Returns [] when nothing was collected.
    """
    rows = (
        ServerMonitoringData.objects
        .filter(test=test)
        .select_related('server')
        .values_list('server__server_name', 'data')
    )

    by_host = {}
    for host, data in rows:
        if not isinstance(data, dict):
            continue
        by_host.setdefault(host or 'unknown', []).append(data)

    hosts = []
    for host, host_rows in sorted(by_host.items()):
        host_rows.sort(key=lambda row: str(row.get('timestamp') or ''))
        cpu = [
            value for value in (_cpu_percent(row) for row in host_rows)
            if value is not None
        ]
        mem = [
            value for value in (_memory_percent(row) for row in host_rows)
            if value is not None
        ]
        loads = [
            value for value in
            (_number(row.get(LOAD_KEY)) for row in host_rows)
            if value is not None
        ]
        hosts.append({
            'host': host,
            'cpu': cpu,
            'mem': mem,
            'la': f'{loads[-1]:.2f}' if loads else '—',
        })
    return hosts
