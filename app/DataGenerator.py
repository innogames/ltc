import pandas as pd
import re
import os
import StringIO
import logging
import fnmatch
from DataBaseAdapter import DataBaseAdapter
from RunningTest import RunningTest
from xml.etree import ElementTree as et

MONITORING_DIR = "/var/lib/jenkins/jobs/"
#MONITORING_DIR = "C:\work\monitoring"
log = logging.getLogger(__name__)

class DataGenerator:
    def __init__(self):
        self.database_adapter = DataBaseAdapter()
        self.running_tests = RunningTestsList()

    def resultset_to_csv(self,data):
        csv = ""
        rownum = 0
        for row in data:
            for column in row:
                csv += str(column) + ","
            csv += "\n"
            rownum+=1
        csv = re.sub(",\n","\n",csv)
        return csv

    def df_to_pivotcsv(self, data,a,b,c):
        df = pd.DataFrame(data)
        df.columns = df.iloc[0]
        df = df.reindex(df.index.drop(0))
        df = df.pivot(a,b,c)
        s = StringIO.StringIO()
        df.to_csv(s)
        return s.getvalue()

    def df_to_csv(self,df):
        s = StringIO.StringIO()
        df.to_csv(s)
        return s.getvalue()

    def df_to_pivotdf(self, data,a,b,c):
        df = pd.DataFrame(data)
        df.columns = df.iloc[0]
        df = df.reindex(df.index.drop(0))
        df_pivot = df.pivot(a,b,c)
        return df_pivot

    def get_running_tests_list(self):
        index = 0
        for root, dirs, files in os.walk(MONITORING_DIR):
            if "workspace" in root:
                for f in fnmatch.filter(files, '*.jtl'):
                    if os.stat(os.path.join(root, f)).st_size>0:
                        index += 1
                        if not any(os.path.join(root, f) in sublist for sublist in self.running_tests.runningTestsList):
                            if len(self.running_tests.runningTestsList)>0:
                                # get the index of last element ^___^ and + 1
                                index = self.running_tests.runningTestsList[-1][0] + 1
                            else:
                                index = 1
                            log.debug( "Add a new running test; index:" + str(index) + " root:" + root)
                            running_test = RunningTest(root, f)
                            self.running_tests.runningTestsList.append([index,os.path.join(root, f), running_test])

            # delete old tests from list
        for running_test in self.running_tests.runningTestsList:
            jmeter_results_file =  running_test[2].getJmeterResultsFile();
            if not os.path.exists(jmeter_results_file):
                self.running_tests.runningTestsList.remove(running_test)
        log.debug( "New running tests number:" + str(len(self.running_tests.runningTestsList)))
        return self.running_tests.runningTestsList

    def get_running_test_data_for_test_id(self, runningtest_id, data):

        running_test = None
        log.debug( "Current running tests number:" + str(len(self.running_tests.runningTestsList)))
        for running_test_ in self.running_tests.runningTestsList:
            log.debug( "runningTest_[0]:" + str(running_test_[0]))
            if int(running_test_[0]) == int(runningtest_id):
                running_test = running_test_[2]
            else:
                log.debug("There is no running test with id:" + str(runningtest_id))
        log.debug("Try to get " + data + " data for test_id:" + str(runningtest_id))
        if data == "rtot_data":
            df = running_test.get_rtot_frame()
            return df
        elif data == "update":
            running_test.update_data_frame()
            return "online data was updated"
        elif data == "aggregate_data":
            df = running_test.get_aggregate_frame()
            return df
        elif data == "successful_requests_percentage":
            df = running_test.get_successful_requests_percentage()
            return df
        elif data == "rps":
            df = running_test.get_last_minute_avg_rps()
            return df
        elif data == "response_codes":
            df = running_test.get_response_codes()
            df = df.pivot(columns='response_code',values='count')
            s = StringIO.StringIO()
            df.to_csv(s, float_format='%.1f', index=False)
            return s.getvalue()

    def get_csv_rtot_for_test_id(self, test_id):
        reader = self.database_adapter.get_rtot_table_for_test_id(test_id)
        print self.resultset_to_csv(reader)
        return self.resultset_to_csv(reader)

    def get_metric_compare_data_for_test_ids(self, test_id_1, test_id_2, server_1, server_2, metric):
        reader = self.database_adapter.get_metric_compare_data_for_test_ids(test_id_1, test_id_2, server_1, server_2, metric)
        x = self.resultset_to_csv(reader)
        return x

    def get_rps_for_test_id(self, test_id):
        reader = self.database_adapter.get_rps_for_test_id(test_id)
        return self.resultset_to_csv(reader)

    def get_csv_compare_rtot(self, test_id_1, test_id_2):
        reader = self.database_adapter.getCompareRTOTDataForTestIds(test_id_1,test_id_2)
        return self.resultset_to_csv(reader)

    def get_errors_percent_for_test_id(self, test_id):
        reader = self.database_adapter.get_errors_percent_for_test_id(test_id)
        return self.resultset_to_csv(reader)

    def get_csv_monitoring_data(self, test_id, server_name, metric):
        reader = self.database_adapter.get_monitoring_data_for_test_id(test_id, server_name, metric)
        data = self.resultset_to_csv(reader)
        print data
        return data

    def get_metric_max_value(self, test_id, server_name, metric):
        reader = self.database_adapter.get_metric_max_value_for_test_id(test_id, server_name, metric)
        return self.resultset_to_csv(reader)

    def get_csv_overall_compare_data(self, project_name):
        res1 = self.database_adapter.get_overall_compare_data_for_project(project_name, "agg_response_times")
        print self.resultset_to_csv(res1)
        res2 = self.database_adapter.get_overall_compare_data_for_project(project_name, "agg_cpu_load")
        print self.resultset_to_csv(res2)
        df1 = pd.DataFrame(res1)
        df2 = self.df_to_pivotdf(res2, 'start_time', 'server_name', 'CPU_LOAD')
        df1.columns = df1.iloc[0]
        df1 = df1.reindex(df1.index.drop(0))
        df1 = df1.set_index(['start_time'])
        m = pd.merge(df1, df2, how='inner', left_index=True, right_index=True)
        m = m.set_index(['Release'])
        s = StringIO.StringIO()
        m.to_csv(s, encoding='utf-8')
        print s.getvalue()
        return s.getvalue()

    def get_csv_bounded_overall_compare_data(self, project_name, test_id_min, test_id_max):
        res1 = self.database_adapter.get_bounded_overall_compare_data_for_project_name(project_name, "agg_response_times",
                                                                                       test_id_min, test_id_max)
        res2 = self.database_adapter.get_bounded_overall_compare_data_for_project_name(project_name, "agg_cpu_load",
                                                                                       test_id_min, test_id_max)
        df1 = pd.DataFrame(res1)
        df2 = self.df_to_pivotdf(res2, 'start_time', 'server_name', 'CPU_LOAD')
        df1.columns = df1.iloc[0]
        df1 = df1.reindex(df1.index.drop(0))
        df1 = df1.set_index(['start_time'])
        m = pd.merge(df1, df2, how='inner', left_index=True, right_index=True)
        m = m.set_index(['Release'])
        s = StringIO.StringIO()
        m.to_csv(s)
        return s.getvalue();

    def get_running_test_data(self, runningtest_id, data):
        if data == 'rtot_data':
            df = self.get_running_test_data_for_test_id(runningtest_id, data)
            s = StringIO.StringIO()
            df.to_csv(s, float_format='%.1f', index=False)
            return s.getvalue()
        elif data == 'update':
            return self.get_running_test_data_for_test_id(runningtest_id, data)
        elif data == 'aggregate_data':
            df = self.get_running_test_data_for_test_id(runningtest_id, data)
            html_code = self.get_html_aggregate_table_from_df(df)
            t = et.fromstring(html_code)
            t.set('id', 'online_aggregate')
            html_code = et.tostring(t)
            return html_code
        elif data == 'successful_requests_percentage':
            successful_requests_percentage = self.get_running_test_data_for_test_id(runningtest_id, data)
            return successful_requests_percentage
        elif data == 'rps':
            rps = self.get_running_test_data_for_test_id(runningtest_id, data)
            return rps
        elif data == 'response_codes':
            response_codes = self.get_running_test_data_for_test_id(runningtest_id, data)
            return response_codes

    def get_last_test_id_for_project_name(self, project_name):
        reader = self.database_adapter.get_last_test_id_for_project_name(project_name)
        return self.resultset_to_csv(reader)

    def get_test_id_for_project_name_and_build_number(self, project_name, build_number):
        reader = self.database_adapter.get_test_id_for_project_name_and_build_number(project_name,build_number)
        return self.resultset_to_csv(reader)

    def get_max_test_id_for_project_name(self, project_name):
        reader = self.database_adapter.get_max_test_id_for_project_name(project_name)
        return self.resultset_to_csv(reader)

    def get_min_test_id_for_project_name(self, project_name):
        reader = self.database_adapter.get_min_test_id_for_project_name(project_name)
        return self.resultset_to_csv(reader)

    def get_html_aggregate_table_from_df(self, df):
        html_code = ""
        html_code += df.to_html(classes="tablesorter")
        return html_code;

    def get_csv_response_times_percentage_compare_table(self,test_id_1,test_id_2, mode):
        reader = self.database_adapter.get_compare_response_times_for_test_ids(test_id_1,test_id_2, mode)
        return self.resultset_to_csv(reader)

    def get_csv_cpu_load_compare_table(self,test_id_1,test_id_2):
        reader = self.database_adapter.get_compare_avg_cpu_load_data_for_test_ids(test_id_1,test_id_2)
        return self.resultset_to_csv(reader)

    def get_csv_rtot_for_url(self, test_id, url):
        reader = self.database_adapter.get_rtot_data_for_url(test_id, url)
        return self.resultset_to_csv(reader)

    def get_csv_errors_for_url(self, test_id, url):
        reader = self.database_adapter.get_errors_data_for_url(test_id, url)
        return self.resultset_to_csv(reader)

    def get_csv_requests_count_for_url(self, test_id, url):
        reader = self.database_adapter.get_requests_count_data_for_url(test_id, url)
        return self.resultset_to_csv(reader)

    def get_html_table_from_resultset(self, reader,table_name):
        html_code = ''
        current_row = 0
        columns_num = 0

        num = 0
        html_code += '<table id="'+table_name+'" class="tablesorter">'
        #   target_csv = PARSED_DATA_ROOT + "aggregate_table.csv"
        for row in reader:  # Read a single row from the CSV file
            # write header row. assumes first row in csv contains header
            if current_row == 0:
                html_code += '<thead><tr>'  # write <tr> tag
                for column in row:
                    columns_num += 1
                    html_code += '<th>' + column + '</th>'
                html_code += '</tr></thead>'

                # write all other rows
            else:
                if current_row % 2 == 0:
                    html_code += '<tr class="alt">'
                else:
                    html_code += '<tr>'
                row_value = [0 for i in xrange(columns_num)]

                check_col = 0

                for column in row:
                    c_value = 0
                    if check_col > 0:
                        try:
                            if column == None:
                                column = 0
                            c_value = float(column)
                        except ValueError, e:
                            print "error", e, column
                            c_value = 0

                        row_value[check_col] = c_value

                    if check_col == 0:
                        html_code += '<td><b>'+ str(column) + '</b></td>'
                    else:
                        html_code += '<td>' + str(column) + '</td>'

                    check_col += 1

                html_code += '</tr>'
            current_row += 1

        html_code += '</table>'
        print html_code
        return html_code;

    #@property
    #@def running_tests(self):
    #    return self.running_tests;

    #@running_tests.setter
    #def running_tests(self, val):
     #   self.running_tests = val

    #def addRunningTest(self, test):
    #    self.running_tests.append(test)
    #    return self.running_tests

class RunningTestsList():
    def __init__(self):
        self._runningTestsList = []

    @property
    def runningTestsList(self):
        print  self._runningTestsList
        return self._runningTestsList;

    @runningTestsList.setter
    def runningTestsList(self, val):
        self._runningTestsList = val

    def append(self, val):
        self.runningTestsList=self.runningTestsList+[val]

