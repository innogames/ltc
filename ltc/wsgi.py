"""
WSGI config for ltc project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os
import sys
from pathlib import Path

# Vendored dependencies (Debian package): /www/ltc/vendor must win over
# system dist-packages. No-op in development checkouts. Keep in sync with
# the same block in manage.py.
_vendor = Path(__file__).resolve().parent.parent / 'vendor'
if _vendor.is_dir():
    sys.path.insert(0, str(_vendor))

from django.core.wsgi import get_wsgi_application  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ltc.settings")

application = get_wsgi_application()
