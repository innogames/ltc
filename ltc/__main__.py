#!/usr/bin/env python3

"""
Load Test Center - Django Application Management

Copyright (c) 2021 InnoGames GmbH
"""

import os
import sys

from django.core.management import execute_from_command_line

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ltc.settings')


def main():
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    sys.path.append('.')
    main()
