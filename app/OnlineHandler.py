import json
import mimetypes
import os
import re
import logging
from BaseHTTPServer import BaseHTTPRequestHandler
from urlparse import urlparse, parse_qs

from HtmlGenerator import HtmlGenerator
from DataGenerator import DataGenerator

class OnlineHandler(BaseHTTPRequestHandler):
    html_generator = HtmlGenerator()
    data_generator = DataGenerator()
    log_file = open('logfile.txt', 'w')
    def log_message(self, format, *args):
        self.log_file.write("%s - - [%s] %s\n" %
                        (self.client_address[0],
                         self.log_date_time_string(),
                         format%args))
    def do_GET(self):
        try:
            response = ""
            print self.path
            if self.path == '/':
                response = self.html_generator.get_html_template()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=UTF8')
                self.end_headers()
                self.wfile.write(response)
            elif "getonlinedata" in self.path:
                p = parse_qs(urlparse(self.path).query)
                action = p['action'][0]
                if action == "getrunningtestslist":
                    response = self.html_generator.get_html_online_page()
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif action == "getrunningtestrtotdata":
                    runningtest_id = p['runningtest_id'][0]
                    response = self.data_generator.get_running_test_data(runningtest_id, 'rtot_data')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif action == "getrunningtestaggregatedata":
                    runningtest_id = p['runningtest_id'][0]
                    response = self.data_generator.get_running_test_data(runningtest_id, 'aggregate_data')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif action == "getrunningtesterrorsratedata":
                    runningtest_id = p['runningtest_id'][0]
                    response = self.data_generator.get_running_test_data(runningtest_id, 'errors_rate_data')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)

            elif "gettestdata" in self.path:
                p = parse_qs(urlparse(self.path).query)
                test_id = p['test_id'][0]
                response = self.html_generator.get_html_page_for_test_id(test_id)
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=UTF8')
                self.end_headers()
                self.wfile.write(response)

            elif "gettestrtotdata" in self.path:
                p = parse_qs(urlparse(self.path).query)
                test_id = p['test_id'][0]
                response = self.data_generator.get_csv_rtot_for_test_id(test_id)
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=UTF8')
                self.end_headers()
                self.wfile.write(response)

            elif "geturldata" in self.path:
                p = parse_qs(urlparse(self.path).query)
                action = p['action'][0]
                test_id = p['test_id'][0]
                url = p['URL'][0]
                if action == "get_rtot":
                    response = self.data_generator.get_csv_rtot_for_url(test_id,url)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                if action == "get_errors":
                    response = self.data_generator.get_csv_errors_for_url(test_id,url)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)

            elif "geturlrtotgraph" in self.path:
                p = parse_qs(urlparse(self.path).query)
                test_id = p['test_id'][0]
                url = p['URL'][0]
                response = self.html_generator.get_html_page_for_url(test_id, url)
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=UTF8')
                self.end_headers()
                self.wfile.write(response)


            elif "gettestslist" in self.path:
                p = parse_qs(urlparse(self.path).query)
                action = p['action'][0]
                project_name = p['project_name'][0]
                if action == "fulllist":
                    response = self.html_generator.get_html_tests_list(project_name)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif action == "lasttestid":
                    response = self.data_generator.get_last_test_id_for_project_name(project_name)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif action == "oldesttest":
                    response = self.data_generator.get_oldest_test_for_project_name(project_name)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif action == "newesttest":
                    response = self.data_generator.get_newest_test_for_project_name(project_name)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
            elif "comparertotdata" in self.path:
                s = re.search('(\[.+?\])', self.path.replace("%22","\"")).group(1)
                jsondata = json.loads(s)
                response = self.data_generator.get_csv_compare_rtot(jsondata[0],jsondata[1])
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=UTF8')
                self.end_headers()
                self.wfile.write(response)
            elif "getmonitoringdata" in self.path:
                p = parse_qs(urlparse(self.path).query)
                test_id = p['test_id'][0]
                server_name = p['server'][0]
                response = self.data_generator.get_csv_monitoring_data(test_id, server_name)
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=UTF8')
                self.end_headers()
                self.wfile.write(response)
            elif "getoverallcomparedata" in self.path:
                print self.path
                p = parse_qs(urlparse(self.path).query)
                project_name = p['project_name'][0]
                action = p['action'][0]
                if action == "all_data":
                    response = self.data_generator.get_csv_overall_compare_data(project_name)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif action == "time_limited_data":
                    time_min = p['time_min'][0]
                    time_max = p['time_max'][0]
                    response = self.data_generator.get_csv_overall_compare_data2(project_name,time_min,time_max)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
            elif "comparetestsdata" in self.path:
                p = parse_qs(urlparse(self.path).query)
                action = p['action'][0]

                if action == "getactionscompareresponsetimes":
                    test_id_1 = p['test_id_1'][0]
                    test_id_2 = p['test_id_2'][0]
                    response = self.data_generator.get_csv_response_times_percentage_compare_table(test_id_1, test_id_2, 'percentage')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif action == "getcpuloadcompare":
                    test_id_1 = p['test_id_1'][0]
                    test_id_2 = p['test_id_2'][0]
                    response = self.data_generator.get_csv_cpu_load_compare_table(test_id_1, test_id_2)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)

            else:
                    self.send_response(200)
                    mimetype, _ = mimetypes.guess_type(os.path.dirname(__file__) + self.path)
                    self.send_header('Content-Type', mimetype)
                    self.end_headers()
                    fhandle = open(os.path.dirname(__file__) + self.path)
                    self.wfile.write(fhandle.read())
                    fhandle.close()


        except IOError:
            logging.warning("404: %s" % self.path)
            self.send_error(404, 'File Not Found: %s' % self.path)
    def do_POST(self):
        try:
            if self.path == '/comparetests':
                self.data_string = self.rfile.read(int(self.headers['Content-Length']))
                jsondata = json.loads(self.data_string)
                response = self.html_generator.get_html_compare_tests_page(jsondata[0], jsondata[1])
                self.send_response(200)
                self.end_headers()
                self.wfile.write(response)
            elif self.path == '/comparertotdata':
                self.data_string = self.rfile.read(int(self.headers['Content-Length']))
                jsondata = json.loads(self.data_string)
                response = self.data_generator.get_csv_compare_rtot(jsondata[0],jsondata[1])
                self.send_response(200)
                self.end_headers()
                self.wfile.write(response)

        except IOError:
            # self.log.warning("404: %s" % self.path)
            self.send_error(404, 'File Not Found: %s' % self.path)




