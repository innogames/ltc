from __future__ import unicode_literals
import pandas as pd
import os
import logging
from pylab import *
from django.db import models

dateconv = np.vectorize(datetime.datetime.fromtimestamp)

# Create your models here.
logger = logging.getLogger(__name__)

class RunningTestsList(object):
    def __init__(self):
        self._runningTestsList = []

    @property
    def runningTestsList(self):
        return self._runningTestsList

    @runningTestsList.setter
    def runningTestsList(self, val):
        self._runningTestsList = val

    def append(self, val):
        self.runningTestsList = self.runningTestsList + [val]

    def remove(self, val):
        self.runningTestsList.remove(val)

    def get_running_test(self, running_test_id):
        running_test = None
        for running_test_ in self.runningTestsList:
            if int(running_test_[0]) == int(running_test_id):
                running_test = running_test_[2]
        return running_test


class RunningTest():
    def __init__(self, path, jtl_file):

        self.start_line = 0
        self.file_size = 0
        self.path = path
        self.jmeter_results_file = os.path.join(self.path, jtl_file)
        self.data_frame = pd.DataFrame()
        self.aggregate_frame = pd.DataFrame()
        self.response_codes_frame = pd.DataFrame()

    def cleanData(self):
        self.rtot_frame = pd.DataFrame()
        self.aggregate_frame = pd.DataFrame()

    def update_data_frame(self):
        num_lines = sum(1 for line in open(self.jmeter_results_file))
        if self.start_line < num_lines - 10:
            read_lines = num_lines - self.start_line - 10
            #if self.file_size < os.path.getsize(self.jmeter_results_file):
            #self.file_size = os.path.getsize(self.jmeter_results_file)
            df = pd.read_csv(
                self.jmeter_results_file,
                index_col=0,
                low_memory=False,
                skiprows=self.start_line,
                nrows=read_lines)
            df.columns = [
                'average', 'URL', 'responseCode', 'success', 'threadName',
                'failureMessage', 'grpThreads', 'allThreads'
            ]
            df = df[~df['URL'].str.contains('exclude_')]
            df.index = pd.to_datetime(dateconv((df.index.values / 1000)))
            # update start line for the next parse
            self.start_line = self.start_line + read_lines

            group_by_response_codes = df.groupby('responseCode')
            add_df = pd.DataFrame()
            add_df['count'] = group_by_response_codes.success.count()
            #add_df['thread_count'] = group_by_response_codes['grpThreads'].nunique()
            add_df = add_df.fillna(0)
            add_df = add_df.reset_index()
            add_df.columns = ['response_code', 'count']
            df1 = pd.concat([self.response_codes_frame, add_df]).groupby(
                'response_code')['count'].sum().reset_index()
            self.response_codes_frame = df1
            #create aggregate table
            group_by_url = df.groupby('URL')  # group date by URLs
            add_aggregate_data = group_by_url.aggregate({
                'average': np.mean
            }).round(1)
            add_aggregate_data['maximum'] = group_by_url.average.max().round(1)
            add_aggregate_data['minimum'] = group_by_url.average.min().round(1)
            add_aggregate_data['count'] = group_by_url.success.count().round(1)
            add_aggregate_data['errors'] = df[(
                df.success == False)].groupby('URL')['success'].count()
            add_aggregate_data = add_aggregate_data.fillna(0)
            add_aggregate_data = add_aggregate_data.reset_index()
            add_aggregate_data.columns = [
                'URL', 'average', 'maximum', 'minimum', 'count', 'errors'
            ]
            #???
            df1 = pd.concat([self.aggregate_frame, add_aggregate_data
                             ]).groupby('URL')['average'].mean().reset_index()
            df2 = pd.concat(
                [self.aggregate_frame, add_aggregate_data]).groupby('URL')[
                    'count', 'errors'].sum().reset_index()
            df3 = pd.concat([self.aggregate_frame, add_aggregate_data
                             ]).groupby('URL')['maximum'].max().reset_index()
            df4 = pd.concat([self.aggregate_frame, add_aggregate_data
                             ]).groupby('URL')['minimum'].min().reset_index()
            result_df = pd.merge(df1, df2, how='inner', on='URL')
            result_df = pd.merge(result_df, df3, how='inner', on='URL')
            result_df = pd.merge(result_df, df4, how='inner', on='URL')
            self.aggregate_frame = result_df
            add_df2 = pd.DataFrame()
            gr_by_minute = df.groupby(pd.TimeGrouper(
                freq='1Min'))  # group data by minute
            add_df2['average'] = gr_by_minute.average.mean()
            add_df2['median'] = gr_by_minute.average.median()
            add_df2['count'] = gr_by_minute.success.count()
            add_df2['errors_count'] = df[(df.success == False)].groupby(
                pd.TimeGrouper(freq='1Min'))['success'].count()
            #add_df2['thread_count'] = gr_by_minute['grpThreads'].nunique()
            #add_df2['rps'] = gr_by_minute.success.count()/60
            add_df2 = add_df2.fillna(0)
            add_df2 = add_df2.reset_index()
            add_df2.columns = [
                'time', 'average', 'median', 'count', 'errors_count'
            ]
            df1 = pd.concat([self.data_frame, add_df2]).groupby('time')[
                'average', 'median'].mean().reset_index()
            df2 = pd.concat([self.data_frame, add_df2]).groupby('time')[
                'count', 'errors_count'].sum().reset_index()
            #df3 = pd.concat([self.data_frame,add_df2]).groupby('time')['thread_count'].max().reset_index()
            result_df = pd.merge(df1, df2, how='inner', on='time')
            #result_df = pd.merge(result_df1, df3, how='inner',on='time')
            result_df['rps'] = result_df['count'] / 60
            #print 'result_df'
            self.data_frame = result_df
            #print self.data_frame
        else:
            logger.info(".jtl file was not changed")

    def successful_requests_percentage(self):
        df = self.data_frame
        req_count = float(df['count'].sum())
        errors_count = float(df['errors_count'].sum())
        successful_requests_percentage = 100 - (errors_count / req_count) * 100
        return successful_requests_percentage

    def last_minute_avg_rps(self):
        df = self.data_frame
        last_minute_req_count = df.iloc[-2, :]['count']
        last_minute_avg_rps = last_minute_req_count / 60
        return last_minute_avg_rps

    def get_response_codes(self):
        return self.response_codes_frame

    def get_rtot_frame(self):
        return self.data_frame

    def get_last_minute_avg_rps(self):
        return self.update_last_minute_avg_rps()

    def get_aggregate_frame(self):
        return self.aggregate_frame

    def get_successful_requests_percentage(self):
        successful_requests_percentage = self.update_successful_requests_percentage(
        )
        return successful_requests_percentage

    def get_jmeter_results_file(self):
        return self.jmeter_results_file
