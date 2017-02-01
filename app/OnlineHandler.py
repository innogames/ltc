import json
import mimetypes
import os
import re
import logging
from BaseHTTPServer import BaseHTTPRequestHandler
from urlparse import urlparse, parse_qs
from HtmlGenerator import HtmlGenerator
from DataGenerator import DataGenerator

log = logging.getLogger(__name__)


class OnlineHandler(BaseHTTPRequestHandler):
    html_generator = HtmlGenerator()

    def do_GET(self):
        try:
            response = ""
            log.info("Incoming HTTP-request:" + self.path)
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
                elif action == "get_online_page":
                    response = self.html_generator.get_html_online_page_body()
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif action == "get_running_test_rtot_data":
                    runningtest_id = p['runningtest_id'][0]
                    response = self.html_generator.get_running_test_data(runningtest_id, 'rtot_data')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif action == "update":
                    runningtest_id = p['runningtest_id'][0]
                    response = self.html_generator.get_running_test_data(runningtest_id, 'update')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif action == "get_running_test_aggregate_data":
                    runningtest_id = p['runningtest_id'][0]
                    response = self.html_generator.get_running_test_data(runningtest_id, 'aggregate_data')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif action == "get_successful_requests_percentage":
                    runningtest_id = p['runningtest_id'][0]
                    response = self.html_generator.get_running_test_data(runningtest_id, 'successful_requests_percentage')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif action == "get_rps":
                    runningtest_id = p['runningtest_id'][0]
                    response = self.html_generator.get_running_test_data(runningtest_id, 'rps')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif action == "get_response_codes":
                    runningtest_id = p['runningtest_id'][0]
                    response = self.html_generator.get_running_test_data(runningtest_id, 'response_codes')
                    print 'get_response_codes'
                    print response
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
            elif "getlasttestdata" in self.path:
                response = self.html_generator.get_html_template()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=UTF8')
                self.end_headers()
                self.wfile.write(response)
            elif "getprojectdata" in self.path:
                response = self.html_generator.get_html_template()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=UTF8')
                self.end_headers()
                self.wfile.write(response)
            elif "getbuilddata" in self.path:
                response = self.html_generator.get_html_template()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=UTF8')
                self.end_headers()
                self.wfile.write(response)
            elif "gettestrtotdata" in self.path:
                p = parse_qs(urlparse(self.path).query)
                test_id = p['test_id'][0]
                response = self.html_generator.get_csv_rtot_for_test_id(test_id)
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
                    response = self.html_generator.get_csv_rtot_for_url(test_id,url)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif action == "get_errors":
                    response = self.html_generator.get_csv_errors_for_url(test_id,url)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                #elif action == "get_requests_count":
                # #   response = self.data_generator.get_csv_requests_count_for_url(test_id,url)
                #    self.send_response(200)
                #    self.send_header('Content-Type', 'text/html; charset=UTF8')
                #    self.end_headers()
                #    self.wfile.write(response)

            elif "geturlrtotgraph" in self.path:
                p = parse_qs(urlparse(self.path).query)
                test_id = p['test_id'][0]
                url = p['URL'][0]
                response = self.html_generator.get_html_page_for_url(test_id, url)
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=UTF8')
                self.end_headers()
                self.wfile.write(response)

            elif "get_test_data" in self.path:
                p = parse_qs(urlparse(self.path).query)
                sub_action = p['sub_action'][0]
                if sub_action == "get_rps":
                    test_id = p['test_id'][0]
                    response = self.html_generator.get_rps_for_test_id(test_id)
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
                    response = self.html_generator.get_last_test_id_for_project_name(project_name)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif action == "min_test_id":
                    response = self.html_generator.get_min_test_id_for_project_name(project_name)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif action == "max_test_id":
                    response = self.html_generator.get_max_test_id_for_project_name(project_name)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif action == "gettestid":
                    build_number = p['build_number'][0]
                    response = self.html_generator.get_test_id_for_project_name_and_build_number(project_name,build_number)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
            elif "comparertotdata" in self.path:
                s = re.search('(\[.+?\])', self.path.replace("%22","\"")).group(1)
                jsondata = json.loads(s)
                response = self.html_generator.get_csv_compare_rtot(jsondata[0],jsondata[1])
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=UTF8')
                self.end_headers()
                self.wfile.write(response)
            elif "get_monitoring_data" in self.path:
                p = parse_qs(urlparse(self.path).query)
                sub_action = p['sub_action'][0]
                if sub_action == 'get_metric_data':
                    test_id = p['test_id'][0]
                    server_name = p['server'][0]
                    metric = p['metric'][0]
                    response = self.html_generator.get_csv_monitoring_data(test_id, server_name, metric)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif sub_action == 'get_metric_compare_data':
                    test_ids = p['test_ids'][0].split(",")
                    servers = p['servers'][0].split(",")
                    metric = p['metric'][0]
                    response = \
                        self.html_generator.get_metric_compare_data_for_test_ids(test_ids[0], test_ids[1], servers[0], servers[1], metric)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif sub_action == 'get_metric_max_value':
                    test_id = p['test_id'][0]
                    server_name = p['server'][0]
                    metric = p['metric'][0]
                    response = self.html_generator.get_metric_max_value(test_id, server_name, metric)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
            elif "getoverallcomparedata" in self.path:
                p = parse_qs(urlparse(self.path).query)
                project_name = p['project_name'][0]
                action = p['action'][0]
                if action == "all_data":
                    response = self.html_generator.get_csv_overall_compare_data(project_name)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif action == "bounded_data":
                    test_id_min = p['test_id_min'][0]
                    test_id_max = p['test_id_max'][0]
                    response = self.html_generator.get_csv_bounded_overall_compare_data(project_name, test_id_min,
                                                                                        test_id_max)
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
                    response = self.html_generator.get_csv_response_times_percentage_compare_table(test_id_1, test_id_2, 'percentage')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=UTF8')
                    self.end_headers()
                    self.wfile.write(response)
                elif action == "getcpuloadcompare":
                    test_id_1 = p['test_id_1'][0]
                    test_id_2 = p['test_id_2'][0]
                    response = self.html_generator.get_csv_cpu_load_compare_table(test_id_1, test_id_2)
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
            log.warning("404: %s" % self.path)
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
                response = self.html_generator.get_csv_compare_rtot(jsondata[0],jsondata[1])
                self.send_response(200)
                self.end_headers()
                self.wfile.write(response)

        except IOError:
            # self.log.warning("404: %s" % self.path)
            self.send_error(404, 'File Not Found: %s' % self.path)




