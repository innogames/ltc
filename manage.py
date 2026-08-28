#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Vendored dependencies (Debian package): /www/ltc/vendor is shipped inside
# the deb and must win over system dist-packages (Puppet may still install
# an older system Django). No-op in development checkouts.
_vendor = Path(__file__).resolve().parent / 'vendor'
if _vendor.is_dir():
    sys.path.insert(0, str(_vendor))

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ltc.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
