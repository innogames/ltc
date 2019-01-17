# Description
JMeter Load Testing Center (codename `jltc`) - dashboard/report analyzer for load testing with JMeter (http://jmeter.apache.org/).

Developed and used in Innogames GmbH (www.innogames.com) to provide load tests results.

Online web-application/dashboard for "continuous integration" (CI) Load testing with JMeter.
A central system for launching (incl. distribution testing), monitoring tests, creating reports and for a comparative analysis between different load tests provided with Jmeter.
Can be used with Jenkins or as a replacement for Jenkins + Plugins + Jmeter combination.

Consist of several modules:

1. Analyzer - build reports, analyze results and compare results with another.
2. Online - online monitoring for running tests
3. Controller - configure and run the tests
4. Administrator - configure different parameters

## [DASHBOARD]
(!) New feature
Upload CSV files with your test results data and get immediately report and compare
it with previous tests:
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/upload.png)

Get tests overview
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/dashboard.png)

## [ANALYZER]
Create dynamic report for the tests
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/report.png)

Get a performance trends for all test results
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/trend_.png)

Get fancy good-readable aggregate table for the test:
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/aggregate.png)

Get detailed report for executed action:
![alt tag](https://github.com/v0devil/jltom/blob/master/pics/action_report_.png)

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
* [nvd3](http://nvd3-community.github.io)

Current `requirements.txt` file is:

```
Django==1.11.16
matplotlib
numpy
pandas
paramiko
psutil
matplotlib
scipy
SQLAlchemy
psycopg2
```

For data storage uses *Postgres (9.5+)*.
Supports Linux and Windows.

## Installation
### 1. Download
You have to download project files in your folder:
    $ cd /home/
    $ git clone git://github.com/innogames/JMeter-Control-Center.git

### 2. Requirements
Right there, you will find the *requirements.txt* file that has all tools, django. To install them, simply type:

`$ pip install -r requirements.txt`

Also probably will be needed to install the next packages:

`$ apt-get install python-matplotlib`

`$ apt-get install python-tk`

### 3. Initialize the database
Create your own or rename the example setting file jtlc/settings.py.example to jtlc/settings.py 

First set the database engine (only PostgreSQL 9.5+) in your settings files; `jltc/settings.py` Of course, remember to install necessary database driver for your engine. Then define your credentials as well.
By default jltc will use `jltc` schema in database, which needs to be created:

`su - postgres`

`psql`

`\c YOUR_DATABASE_NAME`

`CREATE SCHEMA jltc AUTHORIZATION your_user_name;`

Then execute in jltc folder:

`./manage.py makemigrations`

`./manage.py migrate`

`./manage.py loaddata fixtures/initial_data.json`

### 4. Go!
nohup python manage.py runserver 8888 &

### 5. Running tests with Jenkins
Add in Jenkins job those commands, to prepare test plan and run the test:

Jmeter job parameters list example:
```
THREAD_COUNT = 100
DURATION = 3600
RAMPUP = 1800
TEST_PLAN = testplan.jmx
JMETER_DIR = /var/lib/jmeter/
```
Job pre-build action example:
```
duration=$((DURATION + RAMPUP))
TEST_DATA=`python /var/lib/jltc/manage.py shell -c "import controller.views as views; print(views.prepare_test('"$JOB_NAME"','"$WORKSPACE"','"$JMETER_DIR"', '$THREAD_COUNT', '$duration', '$RAMPUP', testplan_file='"$TEST_PLAN"', jenkins_env={'JENKINS_HOME':'"$JENKINS_HOME"','JOB_NAME':'"$JOB_NAME"','BUILD_NUMBER':'"$BUILD_NUMBER"','BUILD_DISPLAY_NAME':'"$BUILD_NUMBER"'}));"`
TEST_PLAN=`python -c 'import json,sys;data=dict('"$TEST_DATA"');print data["testplan"]'`

echo "Test plan: $TEST_PLAN"

VARS="-JTHREAD_COUNT=$THREAD_COUNT -JDURATION=$DURATION -JRAMPUP=$RAMPUP"

java -jar -Xms5g -Xmx5g -Xss256k $JMETER_DIR/bin/ApacheJMeter.jar -n -t $TEST_PLAN -j $WORKSPACE/loadtest.log $VARS -Jjmeter.save.saveservice.default_delimiter=,
```


### 5. Test data analysis with Jenkins
To parse data after the test just add in Jenkins post-job script:
Copy generated result file to current build directory:
```
find "$WORKSPACE" -name jmeter*.jtl -exec mv {} "$JENKINS_HOME/jobs/$JOB_NAME/builds/$BUILD_NUMBER/jmeter.jtl" \;
```
Use datageneration script:
```
./datagenerator_py3.py --jenkins-base-dir /var/jenkins/ --project-name PROJECT_NAME
```
OR

`curl --data "results_dir=$JENKINS_HOME/jobs/$JOB_NAME/builds/$BUILD_NUMBER/" http://localhost:8888/controller/parse_results`


To use with HTML Pulblisher plugin (https://wiki.jenkins.io/display/JENKINS/HTML+Publisher+Plugin) set this values in project setting in Publish HTML reports section:

```
HTML directory to archive: `$JENKINS_HOME/jobs/$JOB_NAME/builds/$BUILD_NUMBER/`
Index page[s]: `https://URL/?action=getbuilddata&project_name=$JOB_NAME&build_number=$BUILD_NUMBER`
Keep past HTML reports: `enabled`
```
