# Description
JMeter Control Center (or `jltom`)

Online web-application for "continuous integration" (CI) Load testing with JMeter.  
A central system for launching (incl. distribution testing), monitoring tests, creating reports and for a comparative analysis between different load tests provided with Jmeter (http://jmeter.apache.org/)
Replacement for Jenkins + Plugins + Jmeter combination, but could be also used in integration with Jenkins CI. 

Consist of several modules:

1. Analyzer - build reports, analyze results and compare results with another.
2. Online - online monitoring for running tests
3. Controller - central part for configuration and starting tests
4. Administrator - configurator for different parameters


## [ANALYZER] 
Get a performance trends for all test results
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/trend_.png)

Create dynamic report for the tests
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/report.png)

Get fancy good-readable aggregate table for the test with graphs for every executed action:
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/aggregate.png)

Get response times, rps, errors data from test:
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/graphs.png)

## [ONLINE] Online test monitoring
Provides online test monitoring, reads .csv result files and builds graphs online without Graphite,plugins,etc:
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/online.png)

## [CONTROLLER]
Configure and start tests, using normal or distribution testing. Possible to configure and run pre- and post-test bash-scripts (currently on development) and additional JMeter test-plan parameters:
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/controller_1.png)


The application comes with:
* [c3.js] (http://c3js.org)
* [jQuery](http://jquery.com/)
* [Twitter Bootstrap](http://getbootstrap.com/)
* [Highlights.js](https://highlightjs.org/)

Current `requirements.txt` file is:

```
python=2.7
django_debug_toolbar==1.7
Django==1.10.5
matplotlib==1.4.3
numpy==1.10.0
pandas==0.17.0
psutil==5.2.1
matplotlib==1.4.3
SQLAlchemy==1.1.3
```

For data storage uses *Postgres (9.5+)*.
Supports Linux and Windows.

## Installation
### 1. Download
You have to download project files in your folder:
    $ cd /home/
    $ git clone git://github.com/v0devil/JMeter-Control-Center.git

### 2. Requirements
Right there, you will find the *requirements.txt* file that has all tools, django. To install them, simply type:

`$ pip install -r requirements.txt`

### 3. Initialize the database
First set the database engine (only PostgreSQL 9.5+) in your settings files; `jltom/settings.py` Of course, remember to install necessary database driver for your engine. Then define your credentials as well.
Then execute:

`./manage.py makemigrations`
`./manage.py migrate`

### 4. Go!
nohup python manage.py runserver 8888 &

### 5. Jenkins

It iss possible to use this application in cooperation with Jenkins. (if to start with Yandex-tank https://github.com/yandex/yandex-tank)
In post-job script you need to add HTTP post request:
`curl --data "results_dir=$JENKINS_HOME/jobs/$JOB_NAME/builds/$BUILD_NUMBER/" http://localhost:8888/controller/parse_results`
OR
include script `datagenerator_linux.py` which will populate database with all necessary data after executed test.