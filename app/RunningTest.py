from pylab import *
import numpy as na
import pandas as pd
import os

dateconv = np.vectorize(datetime.datetime.fromtimestamp)

class RunningTest:
    def __init__(self, path, jtl_file):
        self.start_line = 0
        self.file_size = 0
        self.path = path
        self.jmeter_results_file =  os.path.join(self.path, jtl_file)
        self.rtot_frame = pd.DataFrame()
        self.aggregate_frame = pd.DataFrame()
        self.errors_rate_frame = pd.DataFrame()
    def cleanData(self):
        self.rtot_frame = pd.DataFrame()
        self.aggregate_frame = pd.DataFrame()
        self.errors_rate_frame = pd.DataFrame()

    def update_rtot_frame(self):
        print "start_line:" + str(self.start_line)

        print "file_size:" + str(os.path.getsize(self.jmeter_results_file))
        if self.file_size < os.path.getsize(self.jmeter_results_file):
            self.file_size = os.path.getsize(self.jmeter_results_file)
            print "Adding a new data from .jtl from line: " + str(self.start_line)
            df = pd.read_csv(self.jmeter_results_file, index_col=0, low_memory=False, skiprows=self.start_line)
            df.columns = ['average', 'URL', 'responseCode', 'success', 'threadName', 'failureMessage', 'grpThreads',
                          'allThreads']
            df=df[~df['URL'].str.contains('exclude_')]

            df.index = pd.to_datetime(dateconv((df.index.values / 1000)))
            num_lines = df['average'].count()
            self.start_line = num_lines

            average_rtot = df.groupby(pd.TimeGrouper(freq='1Min')).average.mean().reset_index()
            average_rtot.columns = ['time', 'average']

            median_rtot = df.groupby(pd.TimeGrouper(freq='1Min')).average.median().reset_index()
            median_rtot.columns = ['time', 'median']

            overall_rtot = pd.merge(average_rtot, median_rtot, how='outer', on='time')

            self.rtot_frame = self.rtot_frame.append(overall_rtot)
            #b = os.path.isfile(MONITOR_DIR + "overall_rtot.csv")
            #with open(MONITOR_DIR + "overall_rtot.csv", 'a') as f:
                #overall_rtot.to_csv(f, header=not b, float_format='%.1f', index=False)
        else:
            print ".jtl file was not changed"
        return self.rtot_frame


    def update_aggregate_frame(self):
        df = pd.read_csv(self.jmeter_results_file, index_col=0, low_memory=False)
        df.columns = ['average', 'URL', 'responseCode', 'success', 'threadName', 'failureMessage', 'grpThreads',
                      'allThreads']

        df=df[~df['URL'].str.contains('exclude_')]

        df.index = pd.to_datetime(dateconv((df.index.values / 1000)))
        group_by_url = df.groupby('URL') # group date by URLs
        aggregate_frame = group_by_url.aggregate({'average':np.mean}).round(1)
        aggregate_frame['median'] = group_by_url.average.median().round(1)
        aggregate_frame['75_percentile'] = group_by_url.average.quantile(.75).round(1)
        aggregate_frame['90_percentile'] = group_by_url.average.quantile(.90).round(1)
        aggregate_frame['99_percentile'] = group_by_url.average.quantile(.99).round(1)
        aggregate_frame['maximum'] = group_by_url.average.max().round(1)
        aggregate_frame['minimum'] = group_by_url.average.min().round(1)
        aggregate_frame['count'] = group_by_url.success.count().round(1)
        aggregate_frame['%_errors'] = ((1-df[(df.success == True)].groupby('URL')['success'].count()/group_by_url['success'].count())*100).round(1)
        self.aggregate_frame = aggregate_frame
        return self.aggregate_frame

    def update_errors_rate_frame(self):
        df = pd.read_csv(self.jmeter_results_file, index_col=0, low_memory=False)
        df.columns = ['average', 'URL', 'responseCode', 'success', 'threadName', 'failureMessage', 'grpThreads',
                      'allThreads']
        df=df[~df['URL'].str.contains('exclude_')]
        df.index = pd.to_datetime(dateconv((df.index.values / 1000)))
        self.errors_rate_frame = df.groupby("success").count()
        self.errors_rate_frame = self.errors_rate_frame.transpose()
        return self.errors_rate_frame

    def get_rtot_frame(self):
        return self.update_rtot_frame()

    def get_aggregate_frame(self):
        return self.update_aggregate_frame()

    def get_errors_rate_frame(self):
        return self.update_errors_rate_frame()

    def getJmeterResultsFile(self):
        return self.jmeter_results_file;
