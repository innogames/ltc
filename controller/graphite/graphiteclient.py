import argparse
import hashlib
import hmac
import json
import sys
import time
import logging
from urllib.request import (
    HTTPBasicAuthHandler,
    HTTPPasswordMgrWithDefaultRealm,
    HTTPSHandler,
    build_opener,
    install_opener,
    urlopen,
    quote,
)
from ssl import (
    CERT_NONE,
    create_default_context
)

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description='Graphite metric extraction')
parser.add_argument('-u', '--username', help='Username', default='graphite')
parser.add_argument('-p', '--password', help='Password', required=True)
parser.add_argument('-U', '--url', help='Graphite URL', required=True)
parser.add_argument('-q', '--query', help='Query string', required=True)
parser.add_argument('-f', '--tsfrom', help='Timestamp start')
parser.add_argument('-t', '--tsto', help='Timestamp end')
parser.add_argument(
    '-w', '--warning', type=float,
    help='Warning value threshold', required=True)
parser.add_argument(
    '-c', '--critical', type=float,
    help='Critical value threshold', required=True)


class GraphiteClient(object):
    def __init__(self, url, username, password):
        self.username = username
        self.password = password
        self.token = self._make_token(username, password)
        self.graphite_url = url
        self.url = url

    def _make_token(self, username, password):
        timestamp = str(int(time.time()))
        h = hmac.new(password, digestmod=hashlib.sha256)
        h.update(timestamp)
        h.update(':')
        h.update(username)
        return '{}:{}:{}'.format(h.hexdigest(), timestamp, username)

    def query(self, query, ts_start, ts_end):
        # target = 'summarize({},"{}","avg")'.format(
        #    query, '99year') @TODO remove if not needed

        # build graphite url
        args = {
            '__auth_token': self.token,
            'target': query,
            'format': 'json',
            'from': ts_start,
            'until': ts_end,
        }
        url = '{}/render?'.format(self.url)
        for k, v in args.iteritems():
            url += '{}={}&'.format(quote(k), quote(v))

        logger.debug('Query URL is {}'.format(url))

        # Basic auth header
        password_mgr = HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(
            None,
            self.graphite_url,
            self.username,
            self.password,
        )
        auth_handler = HTTPBasicAuthHandler(password_mgr)

        # Ignore ssl cert check
        ctx = create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = CERT_NONE
        ssl_handler = HTTPSHandler(context=ctx)

        opener = build_opener(ssl_handler, auth_handler)
        install_opener(opener)

        result = json.loads(urlopen(url).read())
        return result


if __name__ == '__main__':
    args = parser.parse_args()

    client = GraphiteClient(args.url, args.username, args.password)
    try:
        value = client.query(args.query, args.tsfrom, args.tsto)
    except Exception as e:
        print('UNKNOWN: Query failed - {}'.format(e))
        sys.exit(3)

    if value >= args.critical:
        print('CRITICAL: {} over {}-{}'.format(value, args.tsfrom, args.tsto))
        sys.exit(2)
    elif value >= args.warning:
        print('WARNING: {} over {}-{}'.format(value, args.tsfrom, args.tsto))
        sys.exit(1)
    else:
        print('OK: {} over {}-{}'.format(value, args.tsfrom, args.tsto))
        sys.exit(0)
