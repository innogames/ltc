from pylab import *
import numpy as na
import pandas as pd
import matplotlib.font_manager
import csv
import sys
import re
import os
import zipfile
from distutils.dir_util import copy_tree
from xml.etree.ElementTree import ElementTree
from os.path import basename

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


builds_dir=sys.argv[1]
report_dir=sys.argv[2]


DATA_DIR = report_dir + "data/"
IMAGES_DIR = report_dir + "images/"
	
build_xml = ElementTree()
for root, dirs, files in os.walk(builds_dir):
	for file in files:
		if "jmeter.jtl" in file:
			if os.stat(os.path.join(root, file)).st_size>0: 
				build_parameters = []
				displayName = "unknown"
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
						elif params.tag == 'displayName':
							displayName = params.text

						
				if "Performance_HTML_Report" not in os.path.join(root, file):									   
					jtl_files.append([os.path.join(root, file),monitoring_data,displayName, build_parameters,root])

			  
jtl_files = sorted(jtl_files, key=getIndex,reverse=True)


  
dateconv = np.vectorize(datetime.datetime.fromtimestamp)
  

aggregate_table='aggregate_table' 
monitor_table='monitor_table'


if not os.path.exists(DATA_DIR):
	os.makedirs(DATA_DIR)
if not os.path.exists(IMAGES_DIR):
	os.makedirs(IMAGES_DIR)


report_html = report_dir + 'report.html' 

print "Try to copy resources dir to report directory: " + report_dir

fromDirectory = "/home/report_gen/resourses/"
toDirectory = report_dir

copy_tree(fromDirectory, toDirectory + "/resourses/")
  
print "Trying to generate HTML-report: %s." % report_html
htmlfile = open(report_html,"w")
  
  
htmlfile.write("""<!DOCTYPE html>
<html>
<head>
<title>Performance Test report</title>
<link rel="stylesheet" type="text/css" href="./resourses/main.css">
<link rel="stylesheet" type="text/css" href="./resourses/blue/style.css">
<link rel="stylesheet" type="text/css" href="./resourses/jquery-ui.css">
<link rel="stylesheet" type="text/css" href="./resourses/c3.css">
<script src='./resourses/jquery-1.11.3.min.js'></script>
<script src='./resourses/jquery-ui.js'></script>
<script src='./resourses/jquery.elevatezoom.js'></script>
<script src='./resourses/jquery.tablesorter.js'></script>
<script src='./resourses/d3.js'></script>
<script src='./resourses/c3.js'></script>
<script>
  $(function() {
	$( "#tabs" ).tabs().addClass('tabs-left');
  });
     $.tablesorter.addParser({ 
        // set a unique id 
        id: 'responsetimes', 
        is: function(s) { 
            // return false so this parser is not auto detected 
            return false; 
        }, 
        format: function(s) { 
            // format your data for normalization 
            return s.replace(/[+]?(\d+).(\d+) ms \(.+?\)/g,"$1.$2"); 
        }, 
        // set type, either numeric or text 
        type: 'numeric' 
    }); 
  
   $(document).ready(function() 
	{ 
		$("#myTable").tablesorter(); 
	} 
   ); 
	 $(document).ready(function() 
	{ 

	var allElements = document.getElementsByTagName("table");
	for (var i = 0, n = allElements.length; i < n; ++i) {
		var el = allElements[i];		
		if (el.id) {
		 if (el.id.indexOf("Table") !== -1)
		{
		 $('#' + el.id).tablesorter(
		 { 
            headers: { 
                2: { 
                    sorter:'responsetimes' 
                },
				4 : { 
                    sorter:'responsetimes' 
                } 
            } 
        }	 
		 
		 );
		 }
		 else{
	    $('#' + el.id).tablesorter();
}
		}
		
	}
		
	} 
   );
 document.onreadystatechange = function () {
  var state = document.readyState
  if (state == 'complete') {
		 document.getElementById('interactive');
		 document.getElementById('load').style.visibility="hidden";
  }
}

  
</script>
</head>
<body><div id="load"></div>""")
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
	checksum = -1
	PARSED_DATA_ROOT = build_root + "/parsed_data/"
	if not os.path.exists(PARSED_DATA_ROOT):
		os.makedirs(PARSED_DATA_ROOT)
	
	if os.path.exists(PARSED_DATA_ROOT + 'checksum'):
		with open(PARSED_DATA_ROOT + 'checksum', 'r') as f:
			checksum = f.readline()
		
		
	
	target_csv = PARSED_DATA_ROOT+"aggregate_table.csv"
	print 'checksum:' +  str(checksum) + '; directory size: ' + str(get_dir_size(PARSED_DATA_ROOT))
	if int(checksum)!=int(get_dir_size(PARSED_DATA_ROOT)) or checksum == -1:
	
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
			chunks = pd.read_table(jmeter_results_file,sep=',',index_col=0,chunksize=5000000);
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
			agg[file_index]['%_errors'] = ((1-df[(df.success == True)].groupby('URL')['success'].count()/byURL['success'].count())*100).round(1)
			
			print "Trying to save aggregate table to CSV-file: %s." % target_csv
			agg[file_index].to_csv(target_csv, sep=',')
			agg[file_index] = pd.read_csv(target_csv, header = 0, names=['URL','average','median','75_percentile','90_percentile','99_percentile','maximum','minimum','count','%_errors'],index_col=0)
			zip_results_file(jmeter_results_file)
		except ValueError,e:
			print "error",e

	
	
		df.groupby(pd.TimeGrouper(freq='10Min')).average.mean().to_csv(PARSED_DATA_ROOT + "average_10.csv", sep=',')
		df.groupby(pd.TimeGrouper(freq='10Min')).average.median().to_csv(PARSED_DATA_ROOT + "median_10.csv", sep=',')  
		df[(df.success == False)].groupby(pd.TimeGrouper(freq='10Min')).success.count().to_csv(PARSED_DATA_ROOT + "overall_errors_10.csv", sep=',')  
		df.groupby("responseCode").average.count().to_csv(PARSED_DATA_ROOT + "response_codes.csv", sep=',')  
		df.groupby("success").average.count().to_csv(PARSED_DATA_ROOT + "errors_rate.csv", sep=',')
		#f.groupby(pd.TimeGrouper(freq='1Min')).success.count().to_csv(PARSED_DATA_ROOT + "count_1.csv", sep=',')

		
		dfURL={}
		uniqueURL = {}
		uniqueURL = df['URL'].unique()
		for URL in uniqueURL:
			URLdist=URL.replace("?", "_").replace("/","_").replace('"',"_")		 
#			if not os.path.exists(PARSED_DATA_ROOT + "average_10_"+URLdist+'.csv') or not os.path.exists(PARSED_DATA_ROOT + "median_10_"+URLdist+'.csv')or not os.path.exists(PARSED_DATA_ROOT + "errors_10_"+URLdist+'.csv'):
			dfURL = df[(df.URL == URL)]
			dfURL.groupby(pd.TimeGrouper(freq='10Min')).average.mean().to_csv(PARSED_DATA_ROOT + "average_10_"+URLdist+'.csv', sep=',')
			dfURL.groupby(pd.TimeGrouper(freq='10Min')).average.median().to_csv(PARSED_DATA_ROOT + "median_10_"+URLdist+'.csv', sep=',')
			dfURL[(dfURL.success == False)].groupby(pd.TimeGrouper(freq='10Min')).success.count().to_csv(PARSED_DATA_ROOT + "errors_10_"+URLdist+'.csv', sep=',')
			#dfURL.groupby(pd.TimeGrouper(freq='1Min')).success.count().to_csv(PARSED_DATA_ROOT + "count_10_"+URLdist+'.csv', sep=',')			
		with open(PARSED_DATA_ROOT + 'checksum', 'w') as f:
			f.write('%d' % get_dir_size(PARSED_DATA_ROOT))		
		
	else:
		print "Using the exist data from " + target_csv
		agg[file_index] = pd.read_csv(target_csv, header = 0, names=['URL','average','median','75_percentile','90_percentile','99_percentile','maximum','minimum','count','%_errors'],index_col=0)
	
	
	
	rtot_over_releases.append([jtl_files[file_index][2],agg[file_index].average.mean(),agg[file_index].average.median()]) 
	file_index += 1
	

   
		

 
htmlfile.write("""<div id="tabs">
  <ul>""")
 
htmlfile.write("""<li><a href='#Overall' style="background-color:#DEB339">Overall</a></li>""")	  
   
for num in range(0,file_index):
	htmlfile.write("<li><a href='#tabs-")
	htmlfile.write(str(num))
	if num == 0:
		if jtl_files[num][2]!="unknown":
			htmlfile.write("'>"+jtl_files[num][2]+" (current)</a></li>")
		else:
			htmlfile.write("'>CURRENT</a></li>")
	else:
		htmlfile.write("'>vs. "+jtl_files[num][2].replace(u'\u200b', '*')+"</a></li>")
		 
	 
htmlfile.write("</ul>")
   
# Open the CSV file for reading

for num in range(0,file_index):
	target_csv = DATA_DIR + "aggregate_table_" + str(num) + ".csv"
	
	df = agg[num]
	
	if num != 0:
		df['average-diff'] = agg[0]['average']-df['average']
	if num != 0:
		df['median-diff'] = agg[0]['median']-df['median']
	if num != 0:
		df['count-diff'] = agg[0]['count']-df['count']
	if num != 0:
		df['%_errors_diff'] = agg[0]['%_errors']-df['%_errors']	
	if num != 0:
		df = df[['average','average-diff','median','median-diff','75_percentile','90_percentile','99_percentile','maximum','minimum','count','count-diff','%_errors','%_errors_diff']]

	if num == 0:
		df.to_csv(target_csv, sep=',')
	else:
		df.to_csv(target_csv, sep=',')
	
num = 0
GRAPHS = ""
for build_root in build_roots:
	uniqueURL = []
	PARSED_DATA_ROOT = build_root + "/parsed_data/"
	htmlfile.write("""<div id="tabs-""")
	htmlfile.write(str(num))
	htmlfile.write("""">""")
 
	htmlfile.write('<ul id="vert_menu"><li><a href="#cpugraphs'+str(num)+'" class="current">cpu graphs</a><a href="#overallgraphs'+str(num)+'" class="current">overall graphs</a><a href="#actiongraphs'+str(num)+'" class="current">action graphs</a></li></ul>');
	rownum = 0
	htmlfile.write('<div class="datagrid" >')
	htmlfile.write('<table id="Table'+ str(num) +'" class="tablesorter">')
#   target_csv = PARSED_DATA_ROOT + "aggregate_table.csv"	
	target_csv = DATA_DIR + "aggregate_table_" + str(num) + ".csv"
	reader = csv.reader(open(target_csv))
	for row in reader: # Read a single row from the CSV file
	# write header row. assumes first row in csv contains header
		if rownum == 0:
			htmlfile.write('<thead><tr>') # write <tr> tag
			for column in row:
				if "URL" not in column and "diff" not in column and "count" not in column and "errors" not in column :
					column = column + " (ms)"
				htmlfile.write('<th>' + column + '</th>')
			htmlfile.write('</tr></thead>')
	   
		  #write all other rows	
		else:
			if rownum%2 == 0:
				htmlfile.write('<tr class="alt">')
			else:
				htmlfile.write('<tr>')
			row_value = [0 for i in xrange(15)]
			check_col = 0	
			for column in row:
				c_value = 0
				if check_col > 0:
					try:
						c_value = float(column)
					except ValueError,e:
						print "error",e,column
						c_value = 0
					 
					row_value[check_col]=c_value		 
						  
				if (check_col==2 or check_col==4 or check_col==13) and num != 0:#diffs
					s = ""
					d = ""
					if(check_col==2 or check_col==4):
						curr = row_value[check_col]
						prev = row_value[check_col-1]
						percent = (round((curr/prev)*100,2) if prev > 0 else 100)
						d = " ms" + ' <b>(' + str(percent) + ' %)</b>'
						if row_value[check_col] > 0:
							s = " +"
					elif (check_col==13):
						d = " %"
						if row_value[check_col] > 0:
							s = " + "					   
										 
					if abs(row_value[check_col])==0 or abs(row_value[check_col-1])==0:
						htmlfile.write('<td style="background-color:#9FFF80">'+ s + column + d + '</td>') 
					elif (abs(row_value[check_col])/row_value[check_col-1])*100<10 or (row_value[check_col]<50 and check_col != 14):
						htmlfile.write('<td style="background-color:#9FFF80">'+ s + column + d + '</td>')
					elif (abs(row_value[check_col])/row_value[check_col-1])*100>10 and row_value[check_col]>0:
						htmlfile.write('<td style="background-color:#FF9999">'+ s + column + d + '</td>')
					else:
						htmlfile.write('<td style="background-color:#66FF33">'+ s + column + d + '</td>')
						 
				elif (check_col==9) and num == 0: #errors for the current release				   
					if c_value>10:
						htmlfile.write('<td style="background-color:#FF9999">' + column + '</td>')
					else:
						htmlfile.write('<td>' + column + '</td>')
				elif (check_col==0):
					uniqueURL.append(column)
					#htmlfile.write('<td><a href="#'+column.replace('/','_')+str(num)+'">' + column +'</a></td>')
					htmlfile.write('<td><b>' + column +'</b></td>')
				else:	
					htmlfile.write('<td>' + column + '</td>')
				 
				check_col+=1
			   
			htmlfile.write('</tr>')
		rownum += 1
   
	print "Created " + str(rownum) + " row table."
	htmlfile.write('</table>')
	 
	font = {'family' : 'sans-serif',
	  #  'weight' : 'bold',
		'size'   : 8}
   
	matplotlib.rc('font', **font)
	 
	 
	htmlfile.write('<table>')
	htmlfile.write('<thead><tr><div id="cpugraphs'+str(num)+'"><th colspan="2">CPU graphs:</th></div></tr></thead>') 
	htmlfile.write("<tr>")
	print "Opening monitoring data:"
	 
	if os.path.isfile(jtl_files[num][1]) and os.stat(jtl_files[num][1]).st_size != 0:
		f = open(jtl_files[num][1],"r")
		lines = f.readlines()
		f.close()
		f = open(jtl_files[num][1],"w")
		for line in lines:
			if not ('start' in line):
				f.write(line)
		 
		f.close()
		monitoring_data = pd.read_csv(jtl_files[num][1],index_col=1, sep=";")
		monitoring_data.columns = ['server_name','Memory_used','Memory_free','Memory_buff','Memory_cached','Net_recv','Net_send','Disk_read','Disk_write','System_la1','CPU_user','CPU_system','CPU_iowait']
		monitoring_data.index=pd.to_datetime(dateconv((monitoring_data.index.values)))
		num_lines = monitoring_data['server_name'].count()
		print "Lines in monitoring data"
		print num_lines
		 
		byServer = monitoring_data.groupby('server_name') 
		mon[num] = byServer.aggregate({'CPU_user':np.mean})
		mon[num]['CPU_user'] = byServer.CPU_user.mean()
		mon[num]['CPU_system'] = byServer.CPU_system.mean()
		mon[num]['CPU_iowait'] = byServer.CPU_iowait.mean()	
		mon[num]['Summary'] = byServer.CPU_iowait.mean()+byServer.CPU_system.mean()+byServer.CPU_user.mean()
   
		summ = mon[num]['Summary']
		summ['Release'] = jtl_files[num][2]
		cpu_over_releases.append([summ])
		print "cpu_over_releases"
		print cpu_over_releases
		rownum_ = 0
		target_csv = IMAGES_DIR+monitor_table+str(num)+'.csv'
		mon[num].to_csv(target_csv, sep=',')
		htmlfile.write('<div class="datagrid">')
		htmlfile.write('<table>')
		reader = csv.reader(open(target_csv))
		 
		for row in reader: # Read a single row from the CSV file
	# write header row. assumes first row in csv contains header
			if rownum_ == 0:
				htmlfile.write('<thead><tr>') # write <tr> tag
				for column in row:
					htmlfile.write('<th>' + column + '</th>')
				htmlfile.write('</tr></thead>')   
			else:
				htmlfile.write('<tr>')
				check_col = 0	
				for column in row: 
					htmlfile.write('<td>' + column + '</td>')												 
				htmlfile.write('</tr>')
			rownum_ += 1
	 
		print "Created " + str(rownum_) + " row table."
		htmlfile.write('</table>')
		 
		server_names = {}
		server_names=monitoring_data['server_name'].unique()
		print "Server names: " + server_names
		for server in server_names:
			dfServer = monitoring_data[(monitoring_data.server_name == server)]
			cpu_user = dfServer.CPU_user
			cpu_system = dfServer.CPU_system
			cpu_iowait = dfServer.CPU_iowait
			 
			fig = plt.figure()
			#p95_rtot = df.groupby(pd.TimeGrouper(freq='10Min')).average.quantile(.95)
			ax = cpu_user.plot(marker='.',markersize=3,title='cpu load ' + str(server) ,label="cpu_user")
			ax = cpu_system.plot(marker='.',markersize=3,title='cpu load ' + str(server) ,label="cpu_system")
			ax = cpu_iowait.plot(marker='.',markersize=3,title='cpu load ' + str(server) ,label="cpu_iowait")
			ax.set_xlabel("Test time")
			ax.set_ylabel("cpu load (%)")
			ax.set_ylim(0,100)
			ax.legend()
			plt.tight_layout()
			destPng = IMAGES_DIR+'cpu_user_'+str(num)  + ' ' +str(server)  + '.png'
			savefig(destPng)
			plt.cla()
			fig.clear()
			htmlfile.write("<td><img src='"+"images/"+'cpu_user_'+str(num)  + ' ' +str(server)   + '.png' +"'></td>")
	else:
		print "Monitoring data is not exist"
	 
	htmlfile.write("</tr>")
	htmlfile.write('<table>')
	 
	 
	average_rtot = pd.read_csv(PARSED_DATA_ROOT + "average_10.csv", index_col=0, header=None,sep=",",names=['time','average'], parse_dates=[0])
	median_rtot = pd.read_csv(PARSED_DATA_ROOT + "median_10.csv", index_col=0, header=None,sep=",",names=['time','median'],parse_dates=[0])
	overall_errors = pd.read_csv(PARSED_DATA_ROOT + "overall_errors_10.csv", index_col=0,header=None,sep=",",names=['time','errors'],parse_dates=[0])
	
	overall_rtot = pd.merge(average_rtot, median_rtot, how='outer', left_index=True, right_index=True)
	overall_rtot.to_csv(DATA_DIR + "overall_rtot_"+str(num)+".csv",float_format='%.1f')
	overall_errors.to_csv(DATA_DIR + "overall_errors_"+str(num)+".csv",float_format='%.1f')
	
	response_codes = pd.read_csv(PARSED_DATA_ROOT + "response_codes.csv",sep=",",header=None,index_col = 0)		
	response_codes.transpose().to_csv(DATA_DIR + "response_codes_"+str(num)+".csv",index=False)
	errors_rate = pd.read_csv(PARSED_DATA_ROOT + "errors_rate.csv",sep=",",header=None,index_col = 0)
	errors_rate.transpose().to_csv(DATA_DIR + "errors_rate_"+str(num)+".csv",index=False)	
  
	
	agg[num][['average']].to_csv(DATA_DIR + "horizontal_"+str(num)+".csv",float_format='%.1f')
	
	  
	htmlfile.write('<table>')
	htmlfile.write('<thead><tr><div id="overallgraphs'+str(num)+'"><th colspan="2">Overall test graphs:</th></div></tr></thead>') 
	htmlfile.write('<tr>')
	htmlfile.write('<td><div id="overall_rtot'+str(num)+'"></div></td>')
	#htmlfile.write('<td><div id="errors_rate'+str(num)+'"></div></td>')
	htmlfile.write('</tr>')
	htmlfile.write('<tr>')
	htmlfile.write('<td><div id="overall_errors'+str(num)+'"></div></td>')
	#htmlfile.write('<td><div id="response_codes'+str(num)+'"></div></td>')
	htmlfile.write('</tr>')
	#htmlfile.write('<tr>')
	#htmlfile.write('<th colspan="2"><div id="horizontal'+str(num)+'"></th>')
	#htmlfile.write('</tr>')
	htmlfile.write('<table>')
	# GRAPHS = GRAPHS + """var response_codes""" + str(num)+ """= c3.generate({
# size: {
		# height: 500,
		# width:500
		# },
	# data: {
		# url: './data/response_codes_""" + str(num)+ """.csv',
		# type : 'donut',
		# onclick: function(e) {
		# //console.log(e);
		# // console.log(d3.select(this).attr("stroke-width","red"));
	  # },
	  # onmouseover: function(d, i) {
		  
	  # },
	  # onmouseout: function(d, i) {

	  # }
		# },
	# title: {
	  # text: 'Response codes on the last test'
	# },bindto: '#response_codes""" + str(num)+ """'
	# });""";
	# GRAPHS = GRAPHS + """var errors_rate""" + str(num)+ """= c3.generate({
# size: {
		# height: 500,
		# width:500
		# },
	# data: {
		# url: './data/errors_rate_""" + str(num)+ """.csv',
		# type : 'donut',
		# colors: {
			# 'False': '#ff0000',
			# 'True': '#00ff00',
		# },
		# onclick: function(e) {
		# //console.log(e);
		# // console.log(d3.select(this).attr("stroke-width","red"));
	  # },
	  # onmouseover: function(d, i) {
		  
	  # },
	  # onmouseout: function(d, i) {

	  # }
		# },
	# title: {
	  # text: 'Errors percentage (%)'
	# },bindto: '#errors_rate""" + str(num)+ """'
	# });""";
	GRAPHS = GRAPHS + """
		var overall_rtot""" + str(num)+ """= c3.generate({
size: {
		height: 700
		},
	data: {
		url: './data/overall_rtot_"""+str(num)+""".csv',
		x:'time',
		xFormat: '%Y-%m-%d %H:%M:%S',
		},
	axis: {
		x: {
			type: 'timeseries',
			tick: {
				format: '%Y-%d-%m %H:%M'
			}
		},
		y: {
			padding: {top:0, bottom:0},
			label: 'response times (ms)',		
		}
		
		}
	,
	title: {
	  text: 'Average und median response times (ms) during a test'
	},bindto: '#overall_rtot"""+ str(num)+"""'
	});""";
	GRAPHS = GRAPHS + """
		var overall_errors""" + str(num)+ """= c3.generate({
size: {
		height: 700
		},
	data: {
		url: './data/overall_errors_"""+str(num)+""".csv',
		x:'time',
		xFormat: '%Y-%m-%d %H:%M:%S',
		},
	axis: {
		x: {
			type: 'timeseries',
			tick: {
				format: '%Y-%d-%m %H:%M'
			}
		},
		y: {
			padding: {top:0, bottom:0},
			label: 'errors',		
		}
		
		}
	,
	title: {
	  text: 'Number of errors per 10 min during a test'
	},bindto: '#overall_errors"""+ str(num)+"""'
	});""";

	# GRAPHS = GRAPHS + """var horizontal""" + str(num)+ """ = c3.generate({
	# bindto: '#horizontal""" + str(num)+ """',
	# size: {
		# height: 700
		# },
	# data: {
		# url: './data/horizontal_0.csv',			// specify that our above json is the data	   
		# x: 'URL',		 // specify that the "name" key is the x value
		# type: 'bar'			// specfify type of plot
	# },
	
	# bar: {
		# width: {
			# ratio: 0.8 // this makes bar width 50% of length between ticks
		# }
		# // or
		# //width: 100 // this makes bar width 100px
	# },
	# axis: {
		# rotated: true,		 // horizontal bar chart
		# x: {
			# type: 'category'   // this needed to load string x value
		# },
		# y: {
			# padding: {top:0, bottom:0},
			# label: 'response time (ms)',		
		# }
	# }
# });""";
	 
	dfURL={}

	
	
	   
	htmlfile.write('<table style="width:100%">')
	htmlfile.write('<thead><tr><div id="actiongraphs'+str(num)+'"><th colspan="1">Action graphs:</th></div></tr></thead>') 
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
		average_rtot_url = pd.read_csv(PARSED_DATA_ROOT + "average_10_"+URL+'.csv', index_col=0,sep=",",parse_dates=[0],names=['time',URL+'_avg'])
		median_rtot_url = pd.read_csv(PARSED_DATA_ROOT + "median_10_"+URL+'.csv', index_col=0,sep=",",parse_dates=[0],names=['time',URL+'_med'])
		#count_url = pd.read_csv(PARSED_DATA_ROOT + "count_10_"+URL+'.csv', index_col=0,sep=",",parse_dates=[0],names=['time',URL+'_cnt'])
		all_url_avg_df = pd.merge(all_url_avg_df, average_rtot_url, how='outer', left_index=True, right_index=True)
		all_url_med_df = pd.merge(all_url_med_df, median_rtot_url, how='outer', left_index=True, right_index=True)
		#all_url_cnt_df = pd.merge(all_url_cnt_df, count_url, how='outer', left_index=True, right_index=True)			
		try:	
			errors_url = pd.read_csv(PARSED_DATA_ROOT + "errors_10_"+URL+'.csv', index_col=0,sep=",",parse_dates=[0],names=['time',URL+'_err'])
			all_url_err_df = pd.merge(all_url_err_df, errors_url, how='outer', left_index=True, right_index=True)
		except ValueError,e:
			print("errors_10_"+URL+'.csv' +' has a zero size')
	all_url_avg_df.to_csv(DATA_DIR + "RTOTs_"+str(num)+".csv",float_format='%.1f')
	all_url_med_df.to_csv(DATA_DIR + "MEDIANs_"+str(num)+".csv",float_format='%.1f')
	all_url_err_df.to_csv(DATA_DIR + "ERRORs_"+str(num)+".csv",float_format='%.1f')
	#all_url_cnt_df.to_csv(DATA_DIR + "COUNTs_"+str(num)+".csv",float_format='%.1f')
	htmlfile.write('<tr><td><div id="rtot'+str(num)+'"></div></td></tr>"')
	htmlfile.write('<tr><td><div id="median'+str(num)+'"></div></td></tr>')
	htmlfile.write('<tr><td><div id="error'+str(num)+'"></div></td></tr>')
	htmlfile.write('</table>')
	if num<5:
		GRAPHS = GRAPHS + """
			var rtot""" + str(num)+ """= c3.generate({
	size: {
			height: 700
			},
		data: {
			url: './data/RTOTs_"""+str(num)+""".csv',
			x:'time',
			xFormat: '%Y-%m-%d %H:%M:%S',
			},
		axis: {
			x: {
				type: 'timeseries',
				tick: {
					format: '%Y-%d-%m %H:%M'
				}
			},
			y: {
				padding: {top:0, bottom:0},
				label: 'response times (ms)',		
			}
			
			}
		,
		title: {
		  text: 'Average response times (ms) for all actions'
		},bindto: '#rtot"""+ str(num)+"""'
		});""";
		GRAPHS = GRAPHS + """
			var median""" + str(num)+ """= c3.generate({
	size: {
			height: 700
			},
		data: {
			url: './data/MEDIANs_"""+str(num)+""".csv',
			x:'time',
			xFormat: '%Y-%m-%d %H:%M:%S',
			},
		axis: {
			x: {
				type: 'timeseries',
				tick: {
					format: '%Y-%d-%m %H:%M'
				}
			},
			y: {
				padding: {top:0, bottom:0},
				label: 'response times (ms)',		
			}
			
			}
		,
		title: {
		  text: 'Median response times (ms) for all actions'
		},bindto: '#median"""+ str(num)+"""'
		});""";
		GRAPHS = GRAPHS + """
			var error""" + str(num)+ """= c3.generate({
	size: {
			height: 700
			},
		data: {
			url: './data/ERRORs_"""+str(num)+""".csv',
			x:'time',
			xFormat: '%Y-%m-%d %H:%M:%S',
			},
		axis: {
			x: {
				type: 'timeseries',
				tick: {
					format: '%Y-%d-%m %H:%M'
				}
			},
			y: {
				padding: {top:0, bottom:0},
				label: 'errors',		
			}
			
			}
		,
		title: {
		  text: 'Error for all actions'
		},bindto: '#error"""+ str(num)+"""'
		});""";
	   

	htmlfile.write('</div>')
	htmlfile.write('</div>')
	num = num + 1
###############################################################################
 
htmlfile.write("""<div id="Overall">""")
htmlfile.write('<div class="datagrid">')
htmlfile.write('<table>') 
font = {'family' : 'sans-serif',
	  #  'weight' : 'bold',
		'size'   : 10} 
aopd = pd.DataFrame(rtot_over_releases, columns=['Release','Average', 'Median'])
aopd = aopd.set_index(['Release'])
aopd = aopd[::-1] #reverse
aopd.to_csv(DATA_DIR+ "RTOT_compare.csv",float_format='%.1f')
ax = aopd.plot(marker='.',markersize=10,title='Average Response Times through all releases',label="average")
ax.set_xlabel("Releases")
ax.set_ylabel("Response time (ms)")
ax.legend()
plt.tight_layout()
destPng = report_dir + "images/rtot_over_releases.png"
savefig(destPng) 
htmlfile.write("<td>")
htmlfile.write('<div class="scrollit">')
 
htmlfile.write(aopd.to_html(classes='table',escape=False,float_format=lambda x: '%10.1f' % x))
htmlfile.write('</div>')
#htmlfile.write("<img src='"+"images/rtot_over_releases.png"+"'>")
htmlfile.write("</td>")
cpu_frames = []
for s in cpu_over_releases:
	print s
	x = pd.DataFrame(s)
	print x
	x = x.set_index(['Release'])
	cpu_frames.append(x)
 
result = pd.concat(cpu_frames)

result = result[::-1]
result.to_csv(DATA_DIR+ "CPU_compare.csv",float_format='%.1f')
cpu_html_table = result.to_html(classes='table',escape=False,float_format=lambda x: '%10.1f' % x)
 
print cpu_html_table
 
m = pd.merge(aopd, result, how='inner', left_index=True, right_index=True)
m.to_csv(DATA_DIR+ "compare.csv",float_format='%.1f')  
 
ax = result.plot(kind='bar',title='Average CPU load on servers through all releases',label="average")
ax.set_xlabel("Releases")
ax.set_ylabel("CPU Load (%)")
ax.set_ylim(0,100)
ax.legend()  
plt.tight_layout()
destPng = report_dir + "images/cpu_over_releases.png"
savefig(destPng) 
 
htmlfile.write("<td>")
htmlfile.write('<div class="scrollit">')
htmlfile.write(cpu_html_table)
htmlfile.write('</div>')
#htmlfile.write("<img src='"+"images/cpu_over_releases.png"+"'>")
htmlfile.write("</td>")
htmlfile.write('</div>')
htmlfile.write('</div>')
htmlfile.write('<div class="datagrid" >')   
htmlfile.write("""<table style="width:100%">
  <tr>
  <th colspan="3"><p style="text-align:center;"><span style="font-family:Cursive;font-size:14px;font-style:normal;font-weight:bold;text-decoration:none;text-transform:none;color:006600;">Data for the last test</span>
</p></th>
  </tr>
  <tr>   
	<th align="center"><div id="errors_rate_last"></div></th>
	<th rowspan="2" align="center"><div id="horizontal_last"></div></th>
  </tr>
  <tr>
  <td align="center"><div id="response_codes_last"></div></td>
  </tr>
  <tr>
  <th colspan="3"><p style="text-align:center;"><span style="font-family:Cursive;font-size:14px;font-style:normal;font-weight:bold;text-decoration:none;text-transform:none;color:006600;">Data for the all tests</span>
</p></th>
  </tr>
  <tr>
  <th colspan="3"><div id="chart"></div></th>
  </tr>
</table>""")   
htmlfile.write('</div>')  
htmlfile.write("""
<script>
	$('#zoom_01').elevateZoom({
	zoomType: "inner",
cursor: "crosshair",
zoomWindowFadeIn: 500,
zoomWindowFadeOut: 750
   }); 
</script>
""")
htmlfile.write('<script src="./resourses/d3.js"></script>')
htmlfile.write('<script src="./resourses/c3.js"></script>')
htmlfile.write('<script src="graphs.js"></script>')
htmlfile.write('</body>')

f2 = open(report_dir+"/graphs.js", 'w')

f2.write("""var response_codes_last= c3.generate({
size: {
		height: 400,
		width:	350
		},
	data: {
		url: './data/response_codes_0.csv',
		type : 'donut',
		onclick: function(e) {
		//console.log(e);
		// console.log(d3.select(this).attr("stroke-width","red"));
	  },
	  onmouseover: function(d, i) {
		  
	  },
	  onmouseout: function(d, i) {

	  }
		},
	title: {
	  text: 'Response codes statistic from the last test'
	},bindto: '#response_codes_last'
	});""")

GRAPHS = GRAPHS + """var errors_rate_last= c3.generate({
size: {
		height: 400,
		width:	350
		},
	data: {
		url: './data/errors_rate_0.csv',
		type : 'donut',
		colors: {
			'False': '#ff0000',
			'True': '#00ff00',
		},
		onclick: function(e) {
		//console.log(e);
		// console.log(d3.select(this).attr("stroke-width","red"));
	  },
	  onmouseover: function(d, i) {
		  
	  },
	  onmouseout: function(d, i) {

	  }
		},
	title: {
	  text: 'Errors percentage (%)'
	},bindto: '#errors_rate_last'
	});""";	
	
f2.write("""var horizontal_last = c3.generate({
	bindto: '#horizontal_last',
	size: {
		height: 900,
		width:1000
		},
	data: {
		url: './data/horizontal_0.csv',			// specify that our above json is the data	   
		x: 'URL',		 // specify that the "name" key is the x value
		type: 'bar'			// specfify type of plot
	},
	
	bar: {
		width: {
			ratio: 0.8 // this makes bar width 50% of length between ticks
		}
		// or
		//width: 100 // this makes bar width 100px
	},
	axis: {
		rotated: true,		 // horizontal bar chart
		x: {
			type: 'category'   // this needed to load string x value
		},
		y: {
			padding: {top:0, bottom:0},
			label: 'response time (ms)',		
		}
	},
		zoom: {
		enabled: true
	},
	title: {
	  text: 'Actions response times from the last test'
	},
});""");
	
f2.write("""var chart = c3.generate({
size: {
		height: 700,
		},
	data: {
		url: './data/compare.csv',
		filter: function (d) {
				return (d.id !== 'Average' && d.id !== 'Median');
			},
		x : 'Release',
		type: 'bar',
		labels: true,
		names: "cpu",
		axes: {
			Average: 'y2',
			Median: 'y2'
		}
		
	},
	legend: {
		show: true,
		position: 'inset',
		inset: {
			anchor: 'top-right',
			x:undefined,
			y: undefined,
			step: undefined
		}
	},
	bar: {
		width: {
			ratio: 0.8 // this makes bar width 50% of length between ticks
		}
		// or
		//width: 100 // this makes bar width 100px
	},
	axis: {
		x: {
			type: 'category',
			tick: {
				rotate: 90,
				multiline: false
			}
		},
		y: {
			max: 100,
			min: 0,
			padding: {top:0, bottom:0},
			label: 'CPU load (%)',		
		},
		y2: {
		min: 0,
		show: true,
		padding: {top:0, bottom:0},
		label:  'Response time (ms)',
		}
	},
	title: {
  text: 'Average response times (ms) and CPU load (%) on servers through all releases'
}
});
setTimeout(function () {
	chart.load({

		url: './data/compare.csv',
				filter: function (d) {
				return (d.id === 'Average' || d.id === 'Median');
			}	,
		type: 'line',
	
	});
}, 1000);""")







f2.write(GRAPHS)
f2.close()