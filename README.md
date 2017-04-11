
# jltom 
Jmeter Load Test Online Monitor

Written on python.

Requirements
python=2.7
django_debug_toolbar==1.7
Django==1.10.5
matplotlib==1.4.3
numpy==1.10.0
pandas==0.17.0
psutil==5.2.1
matplotlib==1.4.3
SQLAlchemy==1.1.3

Uses c3/j3 graphs 
For data storage uses Postgres.

# Description
Online web-application for analyzing JMeter test results and monitoring the running tests.
Designed for integration with Jenkins. In post-job script need to include script datagenerator_linux.py which will populate database with all necessary data

# Overall test history data
Graph with tests history

![alt tag](https://github.com/v0devil/jltom/blob/master/pics/overall.png)

# Test results
Get fancy good-readable aggregate table for the tests:
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/compare_1.png)

Get monitoring data:
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/compare_2.png)

# Online test monitoring
Provides online test monitoring, reads .csv result files and builds graphs online without Graphite,plugins,etc.
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/online2.png)

# Start

nohup /usr/bin/python start.py > log.txt 2>&1 &

