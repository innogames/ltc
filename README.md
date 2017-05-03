# Description
JMeter Control center.

Online web-application for CI Load testing with JMeter, future replacement for Jenkins + Plugins + Jmeter combination. Now it is possible to  analyze JMeter test results and monitoring the running tests which were started in console mode (incl. distribution testing).
Designed for integration with Jenkins. In post-job script need to include script datagenerator_linux.py which will populate database with all necessary data.

Consist of several modules:

1. Analyzer - build reports, analyze results and compare results with another.
2. Online - online monitoring for running tests
3. Controller - central part for configuration and starting tests (currently ready on 60%)


# [ANALYZER] Create dynamic report for tests
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/report.png)

# [ANALYZER] Test results
Get fancy good-readable aggregate table for the test with graphs for every executed action:
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/aggregate.png)

# [ANALYZER] Get response times, rps, errors data from test:
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/graph.png)

# [ONLINE] Online test monitoring
Provides online test monitoring, reads .csv result files and builds graphs online without Graphite,plugins,etc:
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/online.png)

# [CONTROLLER]
Configure and start tests, using normal or distribution testing. Possible to configure and run pre- and post-test bash-scripts (currently on development) and additional JMeter test-plan parameters:
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/controller_1.png)

# JLTOM 
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

# Start

nohup python manage.py runserver 8888 &

