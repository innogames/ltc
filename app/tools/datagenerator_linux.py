from pylab import *
import numpy as na
import pandas as pd
import matplotlib.font_manager
import csv
import sys
import re
import os
import zipfile
import sqlalchemy
from xml.etree.ElementTree import ElementTree
from os.path import basename
from sqlalchemy import create_engine, Table, Column, Index, Integer, String, ForeignKey
from sqlalchemy.sql.expression import func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import reflection
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, TEXT, TIMESTAMP,BIGINT

db_engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
db_connection = db_engine.connect()
meta = sqlalchemy.MetaData(bind=db_connection, reflect=True)
insp = reflection.Inspector.from_engine(db_engine)



if not db_engine.dialect.has_table(db_engine.connect(), "tests"):
    tests = Table('tests', meta,
                  Column('id', Integer, primary_key=True),
                  Column('path', String),
                  Column('display_name', String),
                  Column('project', String),
                  Column('start_time', BIGINT)
                  )
    meta.create_all(db_connection)

if not db_engine.dialect.has_table(db_engine.connect(), "tests_overall_data"):
    tests = Table('tests_overall_data', meta,
                  Column('URL', String),
                  Column('timestamp', TIMESTAMP),
                  Column('test_id', Integer, ForeignKey("tests.id"), nullable=False),
                  Column('avg', DOUBLE_PRECISION),
                  Column('median',DOUBLE_PRECISION)
                  )
    meta.create_all(db_connection)

if not db_engine.dialect.has_table(db_engine.connect(), "tests_url_data"):
    tests = Table('tests_url_data', meta,
                  Column('timestamp', TIMESTAMP),
                  Column('URL', String),
                  Column('test_id', Integer, ForeignKey("tests.id"), nullable=False),
                  Column('avg', DOUBLE_PRECISION),
                  Column('median',DOUBLE_PRECISION),
                  Column('errors',DOUBLE_PRECISION),
                  Index('idx_tud_1', 'test_id', 'URL'),
                  )
    meta.create_all(db_connection)

if not db_engine.dialect.has_table(db_engine.connect(), "aggregate"):
    aggregate = Table('aggregate', meta,
                      Column('test_id', Integer, ForeignKey("tests.id"), nullable=False),
                      Column('URL', String),
                      Column('average', DOUBLE_PRECISION),
                      Column('median', DOUBLE_PRECISION),
                      Column('75_percentile', DOUBLE_PRECISION),
                      Column('90_percentile', DOUBLE_PRECISION),
                      Column('99_percentile', DOUBLE_PRECISION),
                      Column('maximum', DOUBLE_PRECISION),
                      Column('minimum', DOUBLE_PRECISION),
                      Column('count', Integer),
                      Column('errors', Integer),
                      Index('idx_agg_1', 'test_id'),
                      )
    meta.create_all(db_connection)

if not db_engine.dialect.has_table(db_engine.connect(), "tests_monitoring_data"):
    tests = Table('tests_monitoring_data', meta,
                  Column('test_id', Integer, ForeignKey("tests.id"), nullable=False),
                  Column('timestamp', TIMESTAMP),
                  Column('server_name', String),
                  Column('Memory_used', DOUBLE_PRECISION),
                  Column('Memory_free', DOUBLE_PRECISION),
                  Column('Memory_buff', DOUBLE_PRECISION),
                  Column('Memory_cached', DOUBLE_PRECISION),
                  Column('Net_recv', DOUBLE_PRECISION),
                  Column('Net_send', DOUBLE_PRECISION),
                  Column('Disk_read', DOUBLE_PRECISION),
                  Column('Disk_write', DOUBLE_PRECISION),
                  Column('System_la1', DOUBLE_PRECISION),
                  Column('CPU_user', DOUBLE_PRECISION),
                  Column('CPU_system', DOUBLE_PRECISION),
                  Column('CPU_iowait', DOUBLE_PRECISION),
                  Index('idx_tmd_1', 'test_id','server_name'),
                  )
    meta.create_all(db_connection)




tests = meta.tables['tests']
aggregate = meta.tables['aggregate']
tests_overall_data = meta.tables['tests_overall_data']
tests_monitoring_data = meta.tables['tests_monitoring_data']

Session = sessionmaker(bind=db_engine)

db_session = Session()

reload(sys)
sys.setdefaultencoding('utf-8')
matplotlib.style.use('bmh')



def percentile(n):
    def percentile_(x):
        return np.percentile(x, n)
    percentile_.__name__ = 'percentile_%s' % n
    return percentile_

def mask(df, f):
    return df[f(df)]

def getIndex(item):
    print item
    return int(re.search('(\d+)/', item[0]).group(1))

def ord_to_char(v, p=None):
    return chr(int(v))

def get_dir_size(path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            if not f=='checksum':
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
    return total_size

def zip_results_file(file):
    if os.path.exists(file+'.zip'):
        os.remove(file+'.zip')
    print "Move results file " + file + " to zip archive"
    with zipfile.ZipFile(file + ".zip", "w", zipfile.ZIP_DEFLATED,allowZip64 = True) as zip_file:
        zip_file.write(file, basename(file))
    os.remove(file)
    print "File was packed, original file was deleted"

jtl_files = []

builds_dir="/var/lib/jenkins/jobs"

jtl_files = []
releases = []


build_xml = ElementTree()
for root, dirs, files in os.walk(builds_dir):
    for file in files:
        if "jmeter.jtl" in file:
            if os.stat(os.path.join(root, file)).st_size>0:
                build_parameters = []
                displayName = "unknown"
                startTime = 0
                monitoring_data =  os.path.join(root.replace('JMeterCSV','').replace('performance-reports',''), "monitoring.data")
                build_xml_path = os.path.join(root.replace('JMeterCSV','').replace('performance-reports',''), "build.xml")


                if os.path.isfile(build_xml_path):
                    build_xml.parse(build_xml_path)
                    build_tag = build_xml.getroot()


                    for params in build_tag:
                        if params.tag == 'actions':
                            parameters = params.find('.//parameters')
                            for parameter in parameters:
                                name = parameter.find('name')
                                value = parameter.find('value')
                                build_parameters.append([name.text,value.text])
                        elif params.tag == 'startTime':
                            startTime = int(params.text)
                        elif params.tag == 'displayName':
                            displayName = params.text



                if ("Performance_HTML_Report" not in os.path.join(root, file)) and ("_hw_" in os.path.join(root, file)):
                    jtl_files.append([os.path.join(root, file),monitoring_data,displayName, build_parameters,root])
                    if db_session.query(tests.c.id).filter(tests.c.path==root).count()==0:
                        max_test_id = db_connection.execute(func.max(tests.c.id)).scalar()
                        max_test_id = max_test_id if max_test_id is not None else 0
                        print root
                        project_name = re.search('/([^/]+)/builds', root).group(1)
                        stm = tests.insert().values(id=max_test_id+1,path=root,display_name=displayName, project=project_name, start_time=startTime)
                        result = db_connection.execute(stm)
jtl_files = sorted(jtl_files, key=getIndex,reverse=True)


releases.sort();


dateconv = np.vectorize(datetime.datetime.fromtimestamp)


aggregate_table='aggregate_table'
monitor_table='monitor_table'


agg = {}
mon = {}

rtot_over_releases = [];
cpu_over_releases = [];


file_index = 0
print "Trying to open CSV-files"

build_roots = [jtl_files[i][4]  for i in xrange(0,len(jtl_files))]

#dataframe to compare with:

for build_root in build_roots:

    print "Current build directory:" + build_root

    test_id = db_session.query(tests.c.id).filter(tests.c.path==build_root).scalar()

    print "Current test id:" + str(test_id)
    checksum = -1
    PARSED_DATA_ROOT = build_root + "/parsed_data/"
    if db_session.query(aggregate.c.test_id).filter(aggregate.c.test_id==test_id).count()==0:

        df = pd.DataFrame()
        jmeter_results_file = build_root + "/jmeter.jtl"
        if not os.path.exists(jmeter_results_file):
            print "Results file does not exists, try to check archive"
            jmeter_results_zip = jmeter_results_file + ".zip"
            if os.path.exists(jmeter_results_zip):
                print "Archive file was found " + jmeter_results_zip
                with zipfile.ZipFile(jmeter_results_zip, "r") as z:
                    z.extractall(build_root)
        print "Executing a new parse: " + jmeter_results_file + " size: "+ str(os.stat(jmeter_results_file).st_size)
        if os.stat(jmeter_results_file).st_size > 1000007777:
            print "Executing a parse for a huge file"
            chunks = pd.read_table(jmeter_results_file,sep=',',index_col=0,chunksize=3000000);
            for chunk in chunks:
                chunk.columns = ['average', 'URL','responseCode','success','threadName','failureMessage','grpThreads','allThreads']
                chunk=chunk[~chunk['URL'].str.contains('exclude_')]
                df = df.append(chunk);
                print "Parsing a huge file,size: " + str(df.size)
        else:
            df = pd.read_csv(jmeter_results_file,index_col=0,low_memory=False)
            df.columns = ['average', 'URL','responseCode','success','threadName','failureMessage','grpThreads','allThreads']
            df=df[~df['URL'].str.contains('exclude_')]

        df.columns = ['average', 'URL','responseCode','success','threadName','failureMessage','grpThreads','allThreads']
        #convert timestamps to normal date/time
        df.index=pd.to_datetime(dateconv((df.index.values/1000)))
        num_lines = df['average'].count()
        print "Number of lines in file 1: %d." % num_lines


        try:
            byURL = df.groupby('URL') # group date by URLs
            agg[file_index] = byURL.aggregate({'average':np.mean}).round(1)
            agg[file_index]['median'] = byURL.average.median().round(1)
            agg[file_index]['75_percentile'] = byURL.average.quantile(.75).round(1)
            agg[file_index]['90_percentile'] = byURL.average.quantile(.90).round(1)
            agg[file_index]['99_percentile'] = byURL.average.quantile(.99).round(1)
            agg[file_index]['maximum'] = byURL.average.max().round(1)
            agg[file_index]['minimum'] = byURL.average.min().round(1)
            agg[file_index]['count'] = byURL.success.count().round(1)
            agg[file_index]['errors'] = ((1-df[(df.success == True)].groupby('URL')['success'].count()/byURL['success'].count())*100).round(1)
            agg[file_index]['test_id'] = test_id

            print "Insert data to AGGREGATE table:"
            agg[file_index].to_sql("aggregate",db_engine,if_exists='append')
            zip_results_file(jmeter_results_file)
        except ValueError,e:
            print "error",e

        test_overall_data = pd.DataFrame()
        df_gr_by_ts_5min = df.groupby(pd.TimeGrouper(freq='5Min'))
        test_overall_data['avg'] = df_gr_by_ts_5min.average.mean()
        test_overall_data['median'] = df_gr_by_ts_5min.average.median()
        test_overall_data['test_id'] = test_id
        test_overall_data.index.names = ['timestamp']
        print test_overall_data
        test_overall_data.to_sql("tests_overall_data",db_engine,if_exists='append')


        dfURL={}
        uniqueURL = {}
        uniqueURL = df['URL'].unique()
        for URL in uniqueURL:
            URLdist=URL.replace("?", "_").replace("/","_").replace('"',"_")
            #			if not os.path.exists(PARSED_DATA_ROOT + "average_10_"+URLdist+'.csv') or not os.path.exists(PARSED_DATA_ROOT + "median_10_"+URLdist+'.csv')or not os.path.exists(PARSED_DATA_ROOT + "errors_10_"+URLdist+'.csv'):
            dfURL = df[(df.URL == URL)]
            url_data = pd.DataFrame()
            df_url_gr_by_ts_5min = dfURL.groupby(pd.TimeGrouper(freq='5Min'))
            url_data['avg'] = df_url_gr_by_ts_5min.average.mean()
            url_data['median'] = df_url_gr_by_ts_5min.average.median()
            df_url_gr_by_ts_5min_only_errors = dfURL[(dfURL.success == False)].groupby(pd.TimeGrouper(freq='5Min'))
            url_data['errors'] = df_url_gr_by_ts_5min_only_errors.success.count()
            url_data['test_id'] = test_id
            url_data['URL'] = URL
            url_data.index.names = ['timestamp']
            url_data.to_sql("tests_url_data",db_engine,if_exists='append')


        #else:
        #print "Using the exist data from " + target_csv
        #agg[file_index] = pd.read_csv(target_csv, header = 0, names=['URL','average','median','75_percentile','90_percentile','99_percentile','maximum','minimum','count','errors','test_id'],index_col=0)



    #rtot_over_releases.append([jtl_files[file_index][2],agg[file_index].average.mean(),agg[file_index].average.median()])
    file_index += 1


num = 0
GRAPHS = ""
for build_root in build_roots:
    uniqueURL = []
    PARSED_DATA_ROOT = build_root + "/parsed_data/"

    rownum = 0

    if os.path.isfile(jtl_files[num][1]) and os.stat(jtl_files[num][1]).st_size != 0:
        test_id = db_session.query(tests.c.id).filter(tests.c.path==build_root).scalar()

        monitoring_data = pd.read_csv(jtl_files[num][1],index_col=1, sep=";")

        monitoring_data.columns = ['server_name','Memory_used','Memory_free','Memory_buff','Memory_cached','Net_recv','Net_send','Disk_read','Disk_write','System_la1','CPU_user','CPU_system','CPU_iowait']
        monitoring_data.index=pd.to_datetime(dateconv((monitoring_data.index.values)))
        monitoring_data['test_id'] = test_id
        monitoring_data.index.names = ['timestamp']
        num_lines = monitoring_data['server_name'].count()
        print "Lines in monitoring data"
        print num_lines
        if db_session.query(tests_monitoring_data.c.test_id).filter(tests_monitoring_data.c.test_id==test_id).count()==0:
            monitoring_data.to_sql("tests_monitoring_data",db_engine,if_exists='append')
        byServer = monitoring_data.groupby('server_name')
        mon[num] = byServer.aggregate({'CPU_user':np.mean})
        mon[num]['CPU_user'] = byServer.CPU_user.mean()
        mon[num]['CPU_system'] = byServer.CPU_system.mean()
        mon[num]['CPU_iowait'] = byServer.CPU_iowait.mean()
        mon[num]['Summary'] = byServer.CPU_iowait.mean()+byServer.CPU_system.mean()+byServer.CPU_user.mean()
        #mon[num].to_sql("tests_monitoring_data",db_engine,if_exists='append')
        summ = mon[num]['Summary']
        summ['Release'] = jtl_files[num][2]
        cpu_over_releases.append([summ])
        print "cpu_over_releases"
        print cpu_over_releases
        rownum_ = 0

        server_names = {}
        server_names=monitoring_data['server_name'].unique()
        print "Server names: " + server_names
        for server in server_names:
            dfServer = monitoring_data[(monitoring_data.server_name == server)]
            cpu_user = dfServer.CPU_user
            cpu_system = dfServer.CPU_system
            cpu_iowait = dfServer.CPU_iowait

    else:
        print "Monitoring data is not exist"
    num+=1




    dfURL={}




    all_url_avg_df = pd.DataFrame()
    all_url_med_df = pd.DataFrame()
    all_url_err_df = pd.DataFrame()
    #all_url_cnt_df = pd.DataFrame()
    print "Build dataframes data:"+PARSED_DATA_ROOT
    for URL in uniqueURL:
        errors_url = pd.DataFrame()
        average_rtot_url = pd.DataFrame()
        median_rtot_url = pd.DataFrame()
        #count_url = pd.DataFrame()
        print "Generating graphs for %s" % URL
        URL=URL.replace("?", "_").replace("/","_").replace('"',"_")
        #all_url_cnt_df = pd.merge(all_url_cnt_df, count_url, how='outer', left_index=True, right_index=True)
        try:
            errors_url = pd.read_csv(PARSED_DATA_ROOT + "errors_10_"+URL+'.csv', index_col=0,sep=",",parse_dates=[0],names=['time',URL+'_err'])
            all_url_err_df = pd.merge(all_url_err_df, errors_url, how='outer', left_index=True, right_index=True)
        except ValueError,e:
            print("errors_10_"+URL+'.csv' +' has a zero size')

        ###############################################################################


        #font = {'family' : 'sans-serif',
        #  'weight' : 'bold',
        #'size'   : 10}
#aopd = pd.DataFrame(rtot_over_releases, columns=['Release','Average', 'Median'])
#aopd = aopd.set_index(['Release'])
#aopd = aopd[::-1] #reverse


cpu_frames = []
for s in cpu_over_releases:
    print s
    x = pd.DataFrame(s)
    print x
    x = x.set_index(['Release'])
    cpu_frames.append(x)

result = pd.concat(cpu_frames)

result = result[::-1]
cpu_html_table = result.to_html(classes='table',escape=False,float_format=lambda x: '%10.1f' % x)

print cpu_html_table

#m = pd.merge(aopd, result, how='inner', left_index=True, right_index=True)


