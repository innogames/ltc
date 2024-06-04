#!/usr/bin/env python

"""
ltc setup
Copyright (c) 2021, InnoGames GmbH
"""

from setuptools import setup, find_packages
from os import environ
from datetime import datetime

VERSION = '2.0.0'


def get_version():
    return '{}-{}'.format(
        datetime.now().strftime('%y.%m.%d'),
        environ.get('BUILD_NUMBER', '1'))


setup(
    name='ltc',
    description='InnoGames GmbH Load Test Center',
    long_description='Load Test Center',
    author='System Administration Department',
    author_email='g.syomin@gmail.com',
    url='https://https://github.com/innogames/ltc',
    license='Copyright (c) InnoGames GmbH',
    version=get_version(),
    packages=find_packages(),
    include_package_data=True,
)
