import sys
import os
from DataGenerator import DataGenerator
from DataBaseAdapter import DataBaseAdapter


reload(sys)
sys.setdefaultencoding('utf-8')


class HtmlGenerator:

    def __init__(self):
        self.data_generator = DataGenerator()
        self.database_adapter = DataBaseAdapter()
    def trackThis(self, html):
        html = '<div class="spt-trackThis">' + html + '</div>'
        return html

    def get_html_list_label(self,text):
        return '<option disabled selected>'+text+'</option>'

    def get_html_in_div_id(self, id, data):
        data_in_tab = "<div id="+id+">"+data+"</div>"
        return data_in_tab

    def get_html_button(self, label,id,color):
        return '<button class="ui-button ui-widget ui-corner-all" style="background-color:'+ color +'" id="'+id+'">' + label + '</button>'

    def get_html_aggregate_table_for_test_id(self, test_id):
        reader = self.database_adapter.get_aggregate_data_for_test_id(test_id)
        test_display_name = self.data_generator.resultset_to_csv(self.database_adapter.get_test_name_for_test_id(test_id));

        rownum = 0
        num = 0
        uniqueURL = []
        html_code = ""
        html_code += '<hr />'
        html_code += '<h3>Aggregate table</h3>'
        html_code += '<table id="AggregateTable' + str(test_id) + '" class="tablesorter">'
        #   target_csv = PARSED_DATA_ROOT + "aggregate_table.csv"
        for row in reader:  # Read a single row from the CSV file
            # write header row. assumes first row in csv contains header
            if rownum == 0:
                html_code += '<thead><tr>'  # write <tr> tag
                for column in row:
                    if "URL" not in column and "diff" not in column and "count" not in column and "errors" not in column:
                        column = column + " (ms)"
                    html_code += '<th>' + column + '</th>'
                html_code += '</tr></thead>'

                # write all other rows
            else:
                if rownum % 2 == 0:
                    html_code += '<tr class="alt">'
                else:
                    html_code += '<tr>'
                row_value = [0 for i in xrange(15)]
                check_col = 0
                for column in row:
                    c_value = 0
                    if check_col > 0:
                        try:
                            c_value = float(column)
                        except ValueError, e:
                            print "error", e, column
                            c_value = 0

                        row_value[check_col] = c_value

                    if (check_col == 2 or check_col == 4 or check_col == 13) and num != 0:  # diffs
                        s = ""
                        d = ""
                        if (check_col == 2 or check_col == 4):
                            curr = row_value[check_col]
                            prev = row_value[check_col - 1]
                            percent = (round((curr / prev) * 100, 2) if prev > 0 else 100)
                            d = " ms" + ' <b>(' + str(percent) + ' %)</b>'
                            if row_value[check_col] > 0:
                                s = " +"
                        elif (check_col == 13):
                            d = " %"
                            if row_value[check_col] > 0:
                                s = " + "

                        if abs(row_value[check_col]) == 0 or abs(row_value[check_col - 1]) == 0:
                            html_code += '<td style="background-color:#9FFF80">' + s + str(column) + d + '</td>'
                        elif (abs(row_value[check_col]) / row_value[check_col - 1]) * 100 < 10 or (
                                        row_value[check_col] < 50 and check_col != 14):
                            html_code += '<td style="background-color:#9FFF80">' + s + str(column) + d + '</td>'
                        elif (abs(row_value[check_col]) / row_value[check_col - 1]) * 100 > 10 and row_value[
                            check_col] > 0:
                            html_code += '<td style="background-color:#FF9999">' + s + str(column) + d + '</td>'
                        else:
                            html_code += '<td style="background-color:#66FF33">' + s + str(column) + d + '</td>'

                    elif (check_col == 9) and num == 0:  # errors for the current release
                        if c_value > 10:
                            html_code += '<td style="background-color:#FF9999">' + str(column) + '</td>'
                        else:
                            html_code += '<td>' + str(column) + '</td>'
                    elif (check_col == 0):
                        uniqueURL.append(column)
                        # html_code += '<td><a href="#'+column.replace('/','_')+str(num)+'">' + column +'</a></td>')
                        html_code += '<td><b><a href="/geturlrtotgraph/?test_id='+test_id+"&URL="+ str(column) + '" onclick="window.open(this.href, "mywin","left=20,top=20,width=500,height=500,toolbar=1,resizable=0"); return false;  target="_blank">' + str(column) + '</a></b></td>'


                    else:
                        html_code += '<td>' + str(column) + '</td>'

                    check_col += 1

                html_code += '</tr>'
            rownum += 1
        html_code += '</table>'

        return html_code;

    def get_html_select_list(self, id, label, options):
        html_code ='<select name="'+id+'" id="'+id+'">'+self.get_html_list_label(label)+options+'</select>'
        return html_code

    def get_html_template(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        print dir_path
        self.page_template = open(os.path.join(dir_path,'templates','main.html'), 'r').read()
        self.page_template = self.page_template.replace('%select-choice-project-overall%', self.get_html_project_list('select-choice-project-overall'))
        self.page_template = self.page_template.replace('%select-choice-project-compare%', self.get_html_project_list('select-choice-project-compare'))
        return self.page_template

    def get_html_tests_list(self, project_name):
        reader = self.database_adapter.get_tests_list_for_project_name(project_name)
        options = ""
        for row in reader:
            options += '<option value="'+str(row[0])+'">'+str(row[1])+'</option>'
        html_code = ""
        html_code +='<hr/>'
        html_code += self.get_html_button("Get last test report","get_last_report_button","#b30000")+" or "
        html_code += self.get_html_select_list("select-choice-2", "Select 1st test", options)
        html_code += self.get_html_select_list("select-choice-3", "Select 2nd test to compare", options)
        return html_code
    
    def get_html_running_tests_list(self):
        reader = self.data_generator.get_running_tests_list()
        options = ""
        for row in reader:
            options += '<option value="'+str(row[0])+'">'+str(row[1])+'</option>'
        html_code = ""
        html_code += self.get_html_select_list("select-choice-runningtests", "Running tests", options)
        return html_code

    def get_html_online_page(self):
        html_code = ""
        html_code += self.get_html_running_tests_list()
        html_code += '<hr/>'
        html_code += '<div id="tabs_online_data">'
        html_code += '''<ul>
        <li><a href='#online_graphs_tab'>Graphs</a></li>
        <li><a href='#online_tables_tab'>Tables</a></li>
        </ul>'''
        # GRAPHS_TAB
        html_code += self.get_html_in_div_id("online_graphs_tab",
                                         self.get_html_in_div_id("online_graph","")+
                                         self.get_html_in_div_id("online_errors_rate_graph",""));
        html_code += self.get_html_in_div_id("online_tables_tab",self.get_html_in_div_id("online_aggregate_table",""));
        html_code += "</div>"
        return html_code

    def get_html_project_list(self, selectlist_name):
        reader = self.database_adapter.get_project_list()
        options = ""
        for row in reader:
            options += '<option value="'+str(row[0])+'">'+str(row[0])+'</option>'

        html_code = '<div data-role="fieldcontain">'
        html_code += self.get_html_select_list(selectlist_name, "Select project", options)
        html_code += '</div>'
        return html_code

    def get_html_compare_tests_page(self, test_id_1, test_id_2):
        html_code = '<hr/>'
        html_code += '<div id="tabs_compare_tests">'
        html_code += '''<ul>
        <li><a href='#highlights_tab'>Highlights</a></li>
        <li><a href='#comparison_tables_tab'>Comparison tables</a></li>
        </ul>
        '''
        html_code += self.get_html_in_div_id("highlights_tab", self.get_html_compare_tests_highlights(test_id_1, test_id_2))
        html_code += self.get_html_in_div_id("comparison_tables_tab",self.get_html_compare_tests_comparison_tables_tab(test_id_1,test_id_2))
        html_code += '</div>'
        return html_code;

    def get_html_compare_tests_comparison_tables_tab(self,test_id_1,test_id_2):
        html_code = '<hr/>'
        html_code += '<div id="compare_tests_comparison_tables_tabs">'
        html_code += '''<ul>
        <li><a href='#response_times_compare_tab'>Response times compare</a></li>
        <li><a href='#system_utilization_compare_tab'>System utilization compare</a></li>
        </ul>
        '''
        html_code += self.get_html_in_div_id("response_times_compare_tab",
                                         self.get_html_response_times_compare_table(test_id_1,test_id_2))

        html_code += self.get_html_in_div_id("system_utilization_compare_tab",
                                         self.data_generator.get_html_table_from_resultset(
                                             self.database_adapter.get_compare_avg_cpu_load_data_for_test_ids(test_id_1,test_id_2),
                                             "avg_cpu_compare_table_2"))

        html_code += '</div>'
        return html_code
    
    def get_html_compare_tests_highlights(self, test_id_1, test_id_2):
        
        reader = self.database_adapter.get_compare_aggregate_response_times_for_test_ids(test_id_1, test_id_2)
        reasonable_percent = 3
        html_code = "<hr />"
        html_code += '<table>'
        html_code += '<tr><th>Response Times</th></tr>'
        html_code += '<tr><td width="60%">'
        html_code += '<div style="overflow:scroll; width:100%; height: 700px;">'
        html_code += '<b color="red">Negatives:</b>'
        #experemental shit
        headers = reader[0]
        current_column_index = 0
        avg_diff_percent_index = 0
        median_diff_percent_index = 0
        for header in headers:
            if header == "avg_diff_percent":
                avg_diff_percent_index = current_column_index
            elif header == "median_diff_percent":
                median_diff_percent_index = current_column_index
            current_column_index += 1

        html_code += '<ul class="superlistnegative">'
        current_row_index = 0
        for row in reader:
            print row
            if current_row_index > 0:
                if row[avg_diff_percent_index]*100 > (100.0 + reasonable_percent) :
                    html_code += '<li>Action ' + "<b>" +str(row[0])+ "</b>" + " became slower on <b>" + str(round(row[avg_diff_percent_index] * 100 - 100,2)) + "</b> %" + "( "+str(row[2]) +" ms -> " + str(row[1])  +" ms )"+ "</li>"
            current_row_index+=1
        html_code += '</ul>'
        html_code += '<b>Positives:</b>'
        html_code += '<ul class="superlistpositive">'
        current_row_index = 0
        for row in reader:
            print row
            if current_row_index > 0:
                if row[avg_diff_percent_index]*100 < (100.0 - reasonable_percent):
                    x = abs(round(row[avg_diff_percent_index] * 100,2))
                    x = x if x > 100 else abs(x - 100)
                    html_code += '<li>Action ' + "<b>" +str(row[0])+ "</b>" + " became faster on <b>" + str(x) + "</b> %" + "( "+str(row[2]) +" ms -> " + str(row[1])  +" ms )"+ "</li>"
            current_row_index+=1
        html_code += '</ul>'
        html_code += '</div>'
        html_code += '</td>'
        html_code += '<td width="40%">'
        html_code += self.get_html_in_div_id("compare_actions_response_times_graph","");
        html_code += '</td>'
        html_code += '</tr>'
        html_code += '<tr>'
        html_code += '<th>System utilization</th>'
        html_code += '</tr>'
        html_code += '<tr><td>'
        html_code += self.data_generator.get_html_table_from_resultset(self.database_adapter.get_compare_avg_cpu_load_data_for_test_ids(test_id_1,test_id_2),"avg_cpu_compare_table")
        html_code += '</td>'
        html_code += '<td>'
        html_code += self.get_html_in_div_id("compare_cpu_load_graph","");
        html_code += '</td>'
        html_code += '</tr>'
        html_code += '</table>'
        return html_code

    def get_html_response_times_compare_table(self,test_id_1,test_id_2):
        reader = self.database_adapter.getCompareAggregateDataForTestIds(test_id_1,test_id_2)
        return self.data_generator.get_html_table_from_resultset(reader, "aggregate_compare_table")


    def get_html_page_for_test_id(self, test_id):
        aggregate_table = self.get_html_aggregate_table_for_test_id(test_id)
        html_code = '<hr/>'
        html_code += '<div id="tabs_test_data">'
        html_code += '''<ul>
        <li><a href='#aggregate_table_tab' style="background-color:#DEB339">Aggregate table</a></li>
        <li><a href='#rtot_graphs_tab'>Response times graphs</a></li>
        <li><a href='#monitoring_graphs_tab'>Monitoring graphs</a></li>
        </ul>'''
        #AGGREGATE TABLE TAB
        html_code += self.get_html_in_div_id("aggregate_table_tab",aggregate_table)
        #RTOT DATA TAB
        html_code += self.get_html_in_div_id("rtot_graphs_tab",self.get_html_in_div_id("placeforgraph",self.get_html_in_div_id("placeforgraph","")))
        #MONITORING DATA TAB
        reader = self.database_adapter.get_servers_from_test_id(test_id)
        #reader = self.database_adapter.getProjectsList()
        options = ""
        for row in reader:
            options += '<option value="'+str(row[0])+'">'+str(row[0])+'</option>'
        monitoring_graphs_tab = self.get_html_select_list("select-server-0", "Select server", options)
        monitoring_graphs_tab += self.get_html_in_div_id("placeformonitoringgraph","")
        html_code += self.get_html_in_div_id("monitoring_graphs_tab",monitoring_graphs_tab)
        html_code += '</div>'
        return html_code

    def get_html_page_for_url(self, test_id, url):
        html_code = ""
        html_code += """
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <title>Performance Test monitor</title>
        <link rel="stylesheet" type="text/css" href="/static/c3.css">
        <script src='/static/d3.js'></script>
        <script src='/static/c3.js'></script>
        <script>


	    rtot_graph = c3.generate({
                     data: {
                         url: "/geturldata/?action=get_rtot&test_id=%test_id%&URL=%url%",
                         type: 'line',
                         x: 'timestamp',
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
                             padding: {
                                 top: 0,
                                 bottom: 0
                             },
                             label: 'response times (ms)',
                         }

                     },
                      title: {
                                  text: 'Average/median response times (ms) for %url%'
                              },
                     bindto: '#rtotgraph'
                 });
        errors_graph = c3.generate({
                     data: {
                         url: "/geturldata/?action=get_errors&test_id=%test_id%&URL=%url%",
                         type: 'line',
                         x: 'timestamp',
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
                             padding: {
                                 top: 0,
                                 bottom: 0
                             },
                             label: 'errors count',
                         }

                     },
                      title: {
                                  text: 'Errors count for %url%'
                              },
                     bindto: '#errosgraph'
                 });


	    </script>
        </head>
        <body>
        <div id="rtotgraph"></div>

        <div id="errosgraph"></div>
        </body>
        </html>


        """



        html_code = html_code.replace('%test_id%',str(test_id))
        html_code = html_code.replace('%url%',str(url))
        return html_code



