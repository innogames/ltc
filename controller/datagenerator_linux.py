from collections import defaultdict, OrderedDict
import json
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
from sqlalchemy.sql import  select, delete
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import reflection
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, TEXT, TIMESTAMP,BIGINT

db_engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
db_connection = db_engine.connect()
meta = sqlalchemy.MetaData(bind=db_connection, reflect=True, schema="jltom")
insp = reflection.Inspector.from_engine(db_engine)
schema = 'jltom'

project = meta.tables['jltom.project']
test = meta.tables['jltom.test']
test_data = meta.tables['jltom.test_data']
action = meta.tables['jltom.action']
test_action_data = meta.tables['jltom.test_action_data']
server = meta.tables['jltom.server']
aggregate = meta.tables['jltom.aggregate']
server_monitoring_data = meta.tables['jltom.server_monitoring_data']
test_aggregate = meta.tables['jltom.test_aggregate']





Session = sessionmaker(bind=db_engine)

db_session = Session()
#stm = server_monitoring_data.delete()
#result = db_session.execute(stm)
#stm = test_aggregate.delete()
#result = db_session.execute(stm)
#stm = test_action_data.delete()
#result = db_session.execute(stm)
#stm = test_data.delete()
#result = db_session.execute(stm)
#stm = aggregate.delete()
#result = db_session.execute(stm)
#stm = test.delete()
#result = db_session.execute(stm)
#stm = action.delete()
#result = db_session.execute(stm)
#stm = server.delete()
#result = db_session.execute(stm)
#stm = project.delete()
#result = db_session.execute(stm)

db_session.commit()

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

                if "Performance_HTML_Report" not in os.path.join(root, file):
                    jtl_files.append([os.path.join(root, file),monitoring_data,displayName, build_parameters,root])
                    project_name = re.search('/([^/]+)/builds', root).group(1)
                    if db_session.query(project.c.id). \
                            filter(project.c.project_name == project_name).count() == 0:
                        print "Adding new project: " + project_name;
                        stm = project.insert().values(project_name=project_name)
                        result = db_connection.execute(stm)

                    project_id = db_session.query(project.c.id). \
                            filter(project.c.project_name == project_name).scalar()
                    print "Project_id: " + str(project_id)
                    if db_session.query(test.c.path).filter(test.c.path==root).count()==0:
                        build_number = int(re.search('/builds/(\d+)', root).group(1))
                        stm = test.insert().values(path=root,
                                                   display_name=displayName,
                                                   project_id=project_id,
                                                   start_time=startTime,
                                                   build_number=build_number)
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
    test_id = db_session.query(test.c.id).filter(test.c.path==build_root).scalar()
    project_id = db_session.query(test.c.project_id).filter(test.c.id == test_id).scalar()


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
                chunk.columns = ['average', 'url','responseCode','success','threadName','failureMessage','grpThreads','allThreads']
                chunk=chunk[~chunk['URL'].str.contains('exclude_')]
                df = df.append(chunk);
                print "Parsing a huge file,size: " + str(df.size)
        else:
            df = pd.read_csv(jmeter_results_file,index_col=0,low_memory=False)
            df.columns = ['average', 'url','responseCode','success','threadName','failureMessage','grpThreads','allThreads']
            df=df[~df['url'].str.contains('exclude_')]

        df.columns = ['average', 'url','responseCode','success','threadName','failureMessage','grpThreads','allThreads']
        #convert timestamps to normal date/time
        df.index=pd.to_datetime(dateconv((df.index.values/1000)))
        num_lines = df['average'].count()
        print "Number of lines in file 1: %d." % num_lines

        unique_urls = df['url'].unique()
        for url in unique_urls:
            if db_session.query(action.c.id).filter(action.c.url == url).\
                    filter(action.c.project_id == project_id).count() == 0:
                print "Adding new action: " + url
                stm = action.insert().values(url=url,
                                             project_id=project_id,
                                           )
                result = db_connection.execute(stm)

            action_id = db_session.query(action.c.id).filter(action.c.url == url). \
                filter(action.c.project_id == project_id).scalar()
            print "Adding action data: " + url
            df_url = df[(df.url == url)]
            url_data = pd.DataFrame()
            df_url_gr_by_ts = df_url.groupby(pd.TimeGrouper(freq='1Min'))
            url_data['avg'] = df_url_gr_by_ts.average.mean()
            url_data['median'] = df_url_gr_by_ts.average.median()
            url_data['count'] = df_url_gr_by_ts.success.count()
            df_url_gr_by_ts_only_errors = df_url[(df_url.success == False)].groupby(pd.TimeGrouper(freq='1Min'))
            url_data['errors'] = df_url_gr_by_ts_only_errors.success.count()
            url_data['test_id'] = test_id
            url_data['url'] = url
            output_json = json.loads(url_data.
                                     to_json(orient='index',date_format='iso'),
                                 object_pairs_hook=OrderedDict)
            for row in output_json:
                data = {'timestamp': row,
                        'avg': output_json[row]['avg'],
                        'median': output_json[row]['median'],
                        'count': output_json[row]['count'],
                        'url': output_json[row]['url'],
                        'errors': output_json[row]['errors'],
                        'test_id': output_json[row]['test_id'],
                        }
                stm = test_action_data.insert().values(test_id=output_json[row]['test_id'],
                                        action_id=action_id,
                                        data=data
                                        )
                result = db_connection.execute(stm)

        try:
            by_url = df.groupby('url')
            agg[file_index] = by_url.aggregate({'average':np.mean}).round(1)
            agg[file_index]['median'] = by_url.average.median().round(1)
            agg[file_index]['percentile_75'] = by_url.average.quantile(.75).round(1)
            agg[file_index]['percentile_90'] = by_url.average.quantile(.90).round(1)
            agg[file_index]['percentile_99'] = by_url.average.quantile(.99).round(1)
            agg[file_index]['maximum'] = by_url.average.max().round(1)
            agg[file_index]['minimum'] = by_url.average.min().round(1)
            agg[file_index]['count'] = by_url.success.count().round(1)
            agg[file_index]['errors'] = ((1-df[(df.success == True)].groupby('url')['success'].count()/by_url['success'].count())*100).round(1)
            agg[file_index]['weight'] =  by_url.average.sum()
            agg[file_index]['test_id'] = test_id
            action_df = pd.read_sql(db_session.query(action.c.id,action.c.url).
                                    filter(action.c.project_id==project_id).statement,
                                    con = db_session.bind)
            action_df.columns = ['action_id', 'url']
            action_df = action_df.set_index('url')
            agg[file_index].index.names = ['url']
            agg[file_index] = pd.merge(action_df, agg[file_index]
                                       ,left_index=True, right_index=True)
            agg[file_index] = agg[file_index].set_index('action_id')
            print agg[file_index].columns
            agg[file_index].to_sql("aggregate", schema='jltom', con=db_engine, if_exists='append')
            zip_results_file(jmeter_results_file)
        except ValueError,e:
            print "error",e


        #print df.groupby(pd.TimeGrouper(freq='1Min')).average.agg(lambda x: x.to_json(orient='records'))
        test_overall_data = pd.DataFrame()
        df_gr_by_ts = df.groupby(pd.TimeGrouper(freq='1Min'))
        test_overall_data['avg'] = df_gr_by_ts.average.mean()
        test_overall_data['median'] = df_gr_by_ts.average.median()
        test_overall_data['count'] = df_gr_by_ts.average.count()
        test_overall_data['test_id'] = test_id
        output_json = json.loads(test_overall_data.
                                 to_json(orient='index',date_format='iso'),
                                 object_pairs_hook=OrderedDict)
        for row in output_json:
            data = {'timestamp': row, 'avg': output_json[row]['avg'],
                    'median': output_json[row]['median'],
                    'count': output_json[row]['count']}
            stm = test_data.insert().values(test_id=output_json[row]['test_id'],
                                       data=data
                                       )
            result = db_connection.execute(stm)

    file_index += 1


num = 0
GRAPHS = ""
for build_root in build_roots:
    uniqueURL = []
    PARSED_DATA_ROOT = build_root + "/parsed_data/"

    rownum = 0

    if os.path.isfile(jtl_files[num][1]) and os.stat(jtl_files[num][1]).st_size != 0:
        test_id = db_session.query(test.c.id).filter(test.c.path==build_root).scalar()
        f = open(jtl_files[num][1],"r")
        lines = f.readlines()
        f.close()
        f = open(jtl_files[num][1],"w")
        for line in lines:
            if not ('start' in line):
                f.write(line)

        f.close()
        monitoring_df = pd.read_csv(jtl_files[num][1],index_col=1, sep=";")

        monitoring_df.columns = ['server_name',
                                   'Memory_used',
                                   'Memory_free',
                                   'Memory_buff',
                                   'Memory_cached',
                                   'Net_recv',
                                   'Net_send',
                                   'Disk_read',
                                   'Disk_write',
                                   'System_la1',
                                   'CPU_user',
                                   'CPU_system',
                                   'CPU_iowait']
        monitoring_df.index=pd.to_datetime(dateconv((monitoring_df.index.values)))
        monitoring_df.index.names = ['timestamp']

        unique_servers = monitoring_df['server_name'].unique()
        for server_ in unique_servers:
            if db_session.query(server.c.id).\
                    filter(server.c.server_name == server_).count() == 0:
                print "Adding new server: " + server_
                stm = server.insert().values(server_name=server_
                                             )
                result = db_connection.execute(stm)

            server_id = db_session.query(server.c.id).\
                filter(server.c.server_name == server_).scalar()

            if db_session.query(server_monitoring_data.c.test_id).\
                    filter(server_monitoring_data.c.test_id==test_id).\
                    filter(server_monitoring_data.c.server_id==server_id).count()==0:
                df_server = monitoring_df[(monitoring_df.server_name == server_)]
                output_json = json.loads(df_server.
                                         to_json(orient='index',date_format='iso'),
                                         object_pairs_hook=OrderedDict)
                for row in output_json:
                    data = {'timestamp': row,
                            'Memory_used': output_json[row]['Memory_used'],
                            'Memory_free': output_json[row]['Memory_free'],
                            'Memory_buff': output_json[row]['Memory_buff'],
                            'Memory_cached': output_json[row]['Memory_cached'],
                            'Net_recv': output_json[row]['Net_recv'],
                            'Net_send': output_json[row]['Net_send'],
                            'Disk_read': output_json[row]['Disk_read'],
                            'Disk_write': output_json[row]['Disk_write'],
                            'System_la1': output_json[row]['System_la1'],
                            'CPU_user': output_json[row]['CPU_user'],
                            'CPU_system': output_json[row]['CPU_system'],
                            'CPU_iowait': output_json[row]['CPU_iowait']
                            }
                    stm = server_monitoring_data.insert().values(test_id=test_id, server_id=server_id, data=data)
                    result = db_connection.execute(stm)

    else:
        print "Monitoring data is not exist"
    num+=1

stmt = select([
    test.c.id, test.c.path
])
query_result = db_engine.execute(stmt)

print "Cleanup obsolete test results"
for q in query_result:
    test_id = q.id
    test_path = q.path
    print "Check: " + test_path
    if not os.path.exists(q.path):
        print "Deleting test_id:" + str(test_id) + " path:" + test_path
        stm1 = aggregate.delete().where(aggregate.c.test_id == test_id)
        stm2 = server_monitoring_data.delete().where(server_monitoring_data.c.test_id == test_id)
        stm3 = test_action_data.delete().where(test_action_data.c.test_id == test_id)
        stm4 = test_data.delete().where(test_data.c.test_id == test_id)
        stm5 = test.delete().where(test.c.id == test_id)

        result1 = db_connection.execute(stm1)
        result2 = db_connection.execute(stm2)
        result3 = db_connection.execute(stm3)
        result4 = db_connection.execute(stm4)
        result5 = db_connection.execute(stm5)

