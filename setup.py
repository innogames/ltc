#!/usr/bin/env python

"""
ltc setup
Copyright (c) 2021, InnoGames GmbH
"""

from setuptools import setup, find_packages
from subprocess import check_output
from datetime import datetime

VERSION = '2.0.0'


def get_version():
    versions = sorted(check_output(['git', 'tag']).splitlines())
    if len(versions) > 0:
        return str(versions[0])
    else:
        git_hash = check_output(  # NOQA: F841
            ('git', 'log', '--pretty=%h', '-n', '1')).splitlines()[0]
        time = datetime.now().strftime('%Y%m%d%H%M%S')
        suffix = '{time}'.format(time=time)
        return ('{version}b{suffix}'
                .format(version=VERSION, suffix=suffix))

def get_packages():
    yield '.'
    yield 'ltc'
    for package in find_packages('ltc'):
        yield 'ltc.{}'.format(package)


setup(
    name='ltc',
    description='InnoGames GmbH Load Test Center',
    long_description='Load Test Center',
    author='System Administration Department',
    author_email='g.syomin@gmail.com',
    url='https://https://github.com/innogames/ltc',
    license='Copyright (c) InnoGames GmbH',
    version=get_version(),
    #packages=find_packages(),
    packages=list(get_packages()),
    include_package_data=True,
)
