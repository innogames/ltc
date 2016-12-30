import sqlalchemy

from sqlalchemy import create_engine, desc, asc, distinct,or_,between
from sqlalchemy.sql.expression import func,literal,union_all
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import  select
from sqlalchemy.engine import reflection



db_engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
db_connection = db_engine.connect()
meta = sqlalchemy.MetaData(bind=db_connection, reflect=True)
insp = reflection.Inspector.from_engine(db_engine)
Session = sessionmaker(bind=db_engine)
db_session = Session()

tests = meta.tables['tests']
aggregate = meta.tables['aggregate']
tests_overall_data = meta.tables['tests_overall_data']
tests_monitoring_data = meta.tables['tests_monitoring_data']
tests_url_data = meta.tables['tests_url_data']


class DataBaseAdapter:

    def __init__(self):
        return None

    def get_aggregate_data_for_test_id(self, test_id):
        statement = select([
            aggregate.c.URL,
            aggregate.c.average,
            aggregate.c.median,
            aggregate.c['75_percentile'],
            aggregate.c['90_percentile'],
            aggregate.c['99_percentile'],
            aggregate.c.maximum,
            aggregate.c.minimum,
            aggregate.c.count,
            aggregate.c.errors,
        ]).where(aggregate.c.test_id == test_id)
        return self.execute_statement(statement, True)

    def getCompareRTOTDataForTestIds(self, test_id_1, test_id_2):
        ta1 = select([
            tests_overall_data.c.timestamp,
            func.row_number().over(order_by=tests_overall_data.c.timestamp).label('rown'),
            tests_overall_data.c.avg,
            tests_overall_data.c.median,
        ]).where(tests_overall_data.c.test_id == test_id_1)

        ta2 = select([
            tests_overall_data.c.timestamp,
            func.row_number().over(order_by=tests_overall_data.c.timestamp).label('rown'),
            tests_overall_data.c.avg,
            tests_overall_data.c.median,
        ]).where(tests_overall_data.c.test_id == test_id_2)
        t1 = ta1.alias('t1')
        t2 = ta2.alias('t2')
        statement = select([
            t1.c.timestamp.label('timestamp'),
            t1.c.avg.label('avg_test_id_'+str(test_id_1)),
            t1.c.median.label('med_test_id_'+str(test_id_1)),
            t2.c.avg.label('avg_test_id_'+str(test_id_2)),
            t2.c.median.label('med_test_id_'+str(test_id_2))
        ]).where(t1.c.rown == t2.c.rown)

        return self.execute_statement(statement, True)


    def get_compare_aggregate_response_times_for_test_ids(self, test_id_1, test_id_2):

        agg1 = select([
            aggregate.c.URL,
            aggregate.c.average,
            aggregate.c.median

        ]).where(aggregate.c.test_id == test_id_1)

        agg2 = select([
            aggregate.c.URL,
            aggregate.c.average,
            aggregate.c.median,
        ]).where(aggregate.c.test_id == test_id_2)

        a1 = agg1.alias('a1')
        a2 = agg2.alias('a2')
        statement = select([
            a1.c.URL.label('URL'),
            a1.c.average.label('average_1'),
            a2.c.average.label('average_2'),
            (a1.c.average-a2.c.average).label('avg_diff'),
            (a1.c.average/a2.c.average).label('avg_diff_percent'),
            a1.c.median.label('median_1'),
            a2.c.median.label('median_2'),
            (a1.c.median-a2.c.median).label('med_diff'),
            (a1.c.median-a2.c.median).label('med_diff_percent')
        ]).where(a1.c.URL == a2.c.URL)

        return self.execute_statement(statement, True)

    def getCompareAggregateDataForTestIds(self, test_id_1, test_id_2):



        agg1 = select([
            aggregate.c.URL,
            aggregate.c.average,
            aggregate.c.median,
            aggregate.c['75_percentile'],
            aggregate.c['90_percentile'],
            aggregate.c['99_percentile'],
            aggregate.c.maximum,
            aggregate.c.minimum,
            aggregate.c.count,
            aggregate.c.errors
        ]).where(aggregate.c.test_id == test_id_1)

        agg2 = select([
            aggregate.c.URL,
            aggregate.c.average,
            aggregate.c.median,
            aggregate.c['75_percentile'],
            aggregate.c['90_percentile'],
            aggregate.c['99_percentile'],
            aggregate.c.maximum,
            aggregate.c.minimum,
            aggregate.c.count,
            aggregate.c.errors
        ]).where(aggregate.c.test_id == test_id_2)

        a1 = agg1.alias('a1')
        a2 = agg2.alias('a2')
        statement = select([
            a1.c.URL.label('URL'),
            #a1.c.average.label('average'),
            (a1.c.average-a2.c.average).label('avg_diff'),
            #a1.c.median.label('median'),
            (a1.c.median-a2.c.median).label('med_diff'),
            #(a1.c['75_percentile']-a2.c['75_percentile']).label('75_diff'),
            #(a1.c['90_percentile']-a2.c['90_percentile']).label('90_diff'),
            #(a1.c['99_percentile']-a2.c['99_percentile']).label('99_diff'),
            #(a1.c.maximum-a2.c.maximum).label('max_diff'),
            #(a1.c.minimum-a2.c.minimum).label('min_diff'),
            (a1.c.count-a2.c.count).label('count_diff'),
            (a1.c.errors-a2.c.errors).label('errors_diff')
        ]).where(a1.c.URL == a2.c.URL)

        return self.execute_statement(statement, True)

    def get_compare_response_times_for_test_ids(self, test_id_1, test_id_2, mode):

        agg1 = select([
            aggregate.c.URL,
            aggregate.c.average,
            aggregate.c.median,
        ]).where(aggregate.c.test_id == test_id_1)

        agg2 = select([
            aggregate.c.URL,
            aggregate.c.average,
            aggregate.c.median,
        ]).where(aggregate.c.test_id == test_id_2)

        a1 = agg1.alias('a1')
        a2 = agg2.alias('a2')
        if mode == 'absolute':
            statement = select([
                a1.c.URL.label('URL'),
                (a1.c.average-a2.c.average).label('avg_diff'),
              #  (a1.c.median-a2.c.median).label('med_diff'),
            ]).where(a1.c.URL == a2.c.URL)
        elif mode == "percentage":
            statement = select([
                a1.c.URL.label('URL'),
                ((a1.c.average-a2.c.average)/a1.c.average * 100).label('avg_diff'),
             #   ((a2.c.median-a1.c.median)/a1.c.median * 100).label('med_diff'),
            ]).where(a1.c.URL == a2.c.URL).where(or_((a1.c.average-a2.c.average)/a1.c.average>0.01 ,(a1.c.average-a2.c.average)/a1.c.average<-0.01))\
                #.where(or_((a2.c.median-a1.c.median)/a1.c.median>0.01 ,(a2.c.median-a1.c.median)/a1.c.median<-0.01))

        return self.execute_statement(statement, True)

    def getReleasesList(self):
        statement = select([
            tests.c.id,
            tests.c.display_name
        ])
        return self.execute_statement(statement, False)

    def get_tests_list_for_project_name(self, project_name):
        statement = select([
            tests.c.id,
            tests.c.display_name
        ]).where(tests.c.project == project_name).order_by(desc(tests.c.start_time))
        return self.execute_statement(statement, False)

    def get_newest_test_for_project_name(self, project_name):
        stmt = select([
            func.max(tests.c.start_time).label('max_start_time')
        ]).where(tests.c.project == project_name)

        s = stmt.alias('s')
        statement = select([
            tests.c.start_time,
            #tests.c.display_name
        ]).where(tests.c.project == project_name).where(tests.c.start_time==s.c.max_start_time)
        return self.execute_statement(statement, False)

    def get_oldest_test_for_project_name(self, project_name):
        stmt = select([
            func.min(tests.c.start_time).label('min_start_time')
        ]).where(tests.c.project == project_name)

        s = stmt.alias('s')
        statement = select([
            tests.c.start_time,
            #tests.c.display_name
        ]).where(tests.c.project == project_name).where(tests.c.start_time==s.c.min_start_time)
        return self.execute_statement(statement, False)

    def get_compare_avg_cpu_load_data_for_test_ids(self,test_id_1,test_id_2):

        test_1_name = self.execute_statement(select([tests.c.display_name]).where(tests.c.id == test_id_1), False)[0][0]
        test_2_name = self.execute_statement(select([tests.c.display_name]).where(tests.c.id == test_id_2), False)[0][0]

        if test_1_name == test_2_name:
            test_1_name += '_1'
            test_2_name += '_2'

        st1 = select([tests_monitoring_data.c.server_name,
            func.avg(tests_monitoring_data.c.CPU_user+tests_monitoring_data.c.CPU_system+tests_monitoring_data.c.CPU_iowait).label('CPU_LOAD_1'),
                      literal(0).label('CPU_LOAD_2'),
                      ])\
            .where(tests_monitoring_data.c.test_id == tests.c.id)\
            .where(tests.c.id == test_id_1).group_by(tests_monitoring_data.c.server_name)

        st2 = select([
                      tests_monitoring_data.c.server_name,
                      literal(0).label('CPU_LOAD_1'),
                      func.avg(tests_monitoring_data.c.CPU_user+tests_monitoring_data.c.CPU_system+tests_monitoring_data.c.CPU_iowait).label('CPU_LOAD_2')]) \
            .where(tests_monitoring_data.c.test_id == tests.c.id) \
            .where(tests.c.id == test_id_2).group_by(tests_monitoring_data.c.server_name)

        #s1 = st1.alias('s1')
        #s2 = st2.alias('s2')

        qt = union_all(st1, st2).alias("united")

        qr = select([qt.c.server_name, func.sum(qt.c.CPU_LOAD_1).label(test_1_name),
                     func.sum(qt.c.CPU_LOAD_2).label(test_2_name)]).group_by(qt.c.server_name)

        #statement = select([s1.c.server_name,s1.c.CPU_LOAD.label(test_1_name),s2.c.CPU_LOAD.label(test_2_name)])\
        #    .where(s1.c.server_name==s2.c.server_name)

        return self.execute_statement(qr, True)

    def get_project_list(self):
        statement = select([
            distinct(tests.c.project)
        ])
        return self.execute_statement(statement, False)

    def get_last_test_id_for_project_name(self, project_name):
        stmt = select([
            func.max(tests.c.start_time).label('max_start_time')
        ]).where(tests.c.project == project_name)
        s = stmt.alias('s')
        statement = select([
            tests.c.id
        ]).where(tests.c.project == project_name).where(tests.c.start_time==s.c.max_start_time)

        return self.execute_statement(statement, False)

    def get_rtot_table_for_test_id(self, test_id):
        statement = select([
            tests_overall_data.c.timestamp,
            tests_overall_data.c.avg.label('avg_test_id_'+str(test_id)),
            tests_overall_data.c.median.label('median_test_id_'+str(test_id)),
        ]).where(tests_overall_data.c.test_id == test_id)

        #.where(tests_data.c.test_id == test_id)
        # where(tests_data.c.metric == metric)
        return self.execute_statement(statement, True)

    def get_rtot_data_for_url(self, test_id, url):
        statement = select([
            tests_url_data.c.timestamp,
            tests_url_data.c.avg.label('avg_'+url),
            tests_url_data.c.median.label('median_'+url),
        ]).where(tests_url_data.c.test_id == test_id).\
        where(tests_url_data.c.URL == url)

        #.where(tests_data.c.test_id == test_id)
        # where(tests_data.c.metric == metric)
        return self.execute_statement(statement, True)

    def get_errors_data_for_url(self, test_id, url):
        statement = select([
            tests_url_data.c.timestamp,
            tests_url_data.c.errors.label('errors_'+url),
        ]).where(tests_url_data.c.test_id == test_id). \
            where(tests_url_data.c.URL == url)

        #.where(tests_data.c.test_id == test_id)
        # where(tests_data.c.metric == metric)
        return self.execute_statement(statement, True)

    def get_monitoring_data_for_test_id(self, test_id, server_name):
        statement = select([
            tests_monitoring_data.c.timestamp,
            tests_monitoring_data.c.CPU_user,
            tests_monitoring_data.c.CPU_system,
            tests_monitoring_data.c.CPU_iowait
        ]).where(tests_monitoring_data.c.test_id == test_id).where(tests_monitoring_data.c.server_name == server_name)
        return self.execute_statement(statement, True)

    def get_overall_compare_data_for_project(self, project_name, data):
        statement = None;
        if data == 'agg_response_times':
            stmt = select([
                tests.c.start_time,
                func.row_number().over(order_by=tests.c.start_time).label('rown'),
                tests.c.display_name,
                func.avg(aggregate.c.average).label('Average'),
                func.avg(aggregate.c.median).label('Median')
            ]).where(tests.c.project == project_name) \
                .where(aggregate.c.test_id == tests.c.id) \
                .group_by(tests.c.display_name) \
                .group_by(tests.c.start_time) \
                .order_by(asc(tests.c.start_time))
            s = stmt.alias('s')
            statement = select([s.c.start_time,
                                func.concat(s.c.rown, '. ', s.c.display_name).label('Release'),
                                s.c.Average,
                                s.c.Median])

        elif data == 'agg_cpu_load':
            stmt = select([
                tests.c.start_time,
                tests_monitoring_data.c.server_name,
                func.avg(tests_monitoring_data.c.CPU_user+tests_monitoring_data.c.CPU_system+tests_monitoring_data.c.CPU_iowait).label('CPU_LOAD')
            ]).where(tests.c.project == project_name) \
                .where(tests_monitoring_data.c.test_id == tests.c.id) \
                .group_by(tests.c.display_name) \
                .group_by(tests_monitoring_data.c.server_name) \
                .group_by(tests.c.start_time) \
                .order_by(asc(tests.c.start_time))
            s = stmt.alias('s')


            statement = select([s.c.start_time,
                                s.c.server_name,
                                s.c.CPU_LOAD])

        return self.execute_statement(statement, True)

    def get_overall_compare_data_for_project2(self, project_name, data, time_min, time_max):
        statement = None;
        print "time_min: %d; time_max: %d;", (time_min, time_max)

        if data == 'agg_response_times':
            stmt = select([
                tests.c.start_time,
                func.row_number().over(order_by=tests.c.start_time).label('rown'),
                tests.c.display_name,
                func.avg(aggregate.c.average).label('Average'),
                func.avg(aggregate.c.median).label('Median')
            ]).where(tests.c.project == project_name) \
                .where(aggregate.c.test_id == tests.c.id) \
                .where(between(tests.c.start_time, int(time_min), int(time_max))) \
                .group_by(tests.c.display_name) \
                .group_by(tests.c.start_time) \
                .order_by(asc(tests.c.start_time))
            s = stmt.alias('s')
            statement = select([s.c.start_time,
                                func.concat(s.c.rown, '. ', s.c.display_name).label('Release'),
                                s.c.Average,
                                s.c.Median])

        elif data == 'agg_cpu_load':
            stmt = select([
                tests.c.start_time,
                tests.c.display_name.label('Release'),
                tests_monitoring_data.c.server_name,
                func.avg(tests_monitoring_data.c.CPU_user+tests_monitoring_data.c.CPU_system+tests_monitoring_data.c.CPU_iowait).label('CPU_LOAD')
            ]).where(tests.c.project == project_name) \
                .where(tests_monitoring_data.c.test_id == tests.c.id) \
                .where(between(tests.c.start_time, int(time_min), int(time_max))) \
                .group_by(tests.c.display_name) \
                .group_by(tests_monitoring_data.c.server_name) \
                .group_by(tests.c.start_time) \
                .order_by(asc(tests.c.start_time))
            s = stmt.alias('s')
            statement = select([s.c.start_time,
                                s.c.server_name,
                                s.c.CPU_LOAD])

        return self.execute_statement(statement, True)

    def get_servers_from_test_id(self, test_id):

        statement = select([
            distinct(tests_monitoring_data.c.server_name)
        ]).where(tests_monitoring_data.c.test_id == test_id)

        #.where(tests_data.c.test_id == test_id)
        # where(tests_data.c.metric == metric)
        return self.execute_statement(statement, False)

    def get_test_name_for_test_id(self, test_id):
        statement = select([
            tests.c.display_name
        ]).where(tests.c.id == test_id)
        return self.execute_statement(statement, False)

    def execute_statement(self, statement, with_header):
        print "Executing SQL-query:%s",str(statement)
        q = db_engine.execute(statement)
        output = []
        fieldnames = []

        for fieldname in q.keys():
            fieldnames.append(fieldname)

        if with_header:
            output.append(fieldnames)

        for row in q.fetchall():
            values = []
            for fieldname in fieldnames:
                values.append(row[fieldname])

            output.append(values)
        return output

