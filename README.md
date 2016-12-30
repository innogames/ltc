
# jltom 
Jmeter Load Test Online Monitor
# Description
Online web-application for analyzing JMeter test results and monitoring the current running tests.
For data storage uses Postgres.

Designed for integration with Jenkins. In post-job script need to include script datagenerator_linux.py which will populate database with all necessary data

# Overall test history data
Graph with tests history

![alt tag](https://github.com/v0devil/jltom/blob/master/pics/overall.png)

# Test results
Get fancy good-readable aggregate table for the tests:
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/compare_1.png)

Get monitoring data:
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/compare_2.png)

# Start

nohup /usr/bin/python start.py > log.txt 2>&1 &

