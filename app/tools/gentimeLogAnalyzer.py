from pylab import *
import numpy as na
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.font_manager
import csv
import sys
import re
import os

reload(sys)
sys.setdefaultencoding('utf-8')
matplotlib.style.use('ggplot')

dateconv = np.vectorize(datetime.datetime.fromtimestamp)

work_dir = "C:\\work\\"
gentime_log_dest = work_dir + "gen_time.log.csv"

df = pd.read_csv(gentime_log_dest,index_col=0,low_memory=False,delimiter=" ")
df.columns = ['URL','gentime','dbtime','num']

#Exclude shit
#df=df[~df['URL'].str.contains('\.php|\.js|\.css|\.ico|\.txt|\.xml|admin/',regex = True)]
df=df[~df['URL'].str.contains('\..+?$',regex = True)]
df=df[~df['URL'].str.contains('admin/')]
#df=df[~df['URL'].str.contains('\.php|\.js',regex = True)]
#df=df[~df['URL'].str.contains('.js')]
#df=df[~df['URL'].str.contains('.css')]
#df=df[~df['URL'].str.contains('.ico')]
#df=df[~df['URL'].str.contains('.txt')]
#df=df[~df['URL'].str.contains('.xml')]
#df=df[~df['URL'].str.contains('.xml')]
#df=df[~df['URL'].str.contains('/admin/')]

#Replace shit
df['URL'].replace('MAP.+?/','N/',inplace=True, regex=True)
df['URL'].replace('\d+','N',inplace=True, regex=True)


df.index=pd.to_datetime(df.index.values)

num_lines = df['URL'].count()

print "Number of lines in gentime log: %d." % num_lines

byURL = df.groupby('URL');
byURL.gentime.count().to_csv(work_dir + "agg.csv", sep=',',header=['COUNT'])



count = df.groupby(pd.TimeGrouper(freq='60Min')).gentime.count()
count.columns = ['time','count']
count.to_csv(work_dir + "count_10.csv", sep=',')

print count.max()
#Most loaded hour
print count.idxmax()

countURL = df.groupby([pd.TimeGrouper(freq='60Min'),'URL']).gentime.count()
countURL.columns = ['time','count']
countURL.to_csv(work_dir + "count_by_url.csv", sep=',')

fig = plt.figure()
ax = fig.add_subplot(1,1,1)
ax.plot(count.index.to_pydatetime(),count,marker='.',markersize=10,label="count")
ax.set_title('Actions over Time')
ax.set_xlabel("Time")
ax.set_ylabel("count")
ax.legend()
plt.gcf().autofmt_xdate()
plt.tight_layout()
savefig(work_dir+'count.png')
plt.cla()
fig.clear()

uniqueURL = df['URL'].unique()

