#!/usr/bin/env python

"""
jltc setup
Copyright (c) 2010, InnoGames GmbH
"""

from setuptools import find_packages, setup
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
    yield 'jltc'
    for package in find_packages('jltc'):
        yield 'jltc.{}'.format(package)


setup(
    name='jltc',
    description='InnoGames GmbH Load Test Center',
    long_description='Load Test Center',
    author='System Administration Department',
    author_email='g.syomin@gmail.com',
    url='https://https://github.com/innogames/JMeter-Control-Center',
    license='Copyright (c) InnoGames GmbH',
    version=get_version(),
    packages=list(get_packages()),
    include_package_data=True,
)
