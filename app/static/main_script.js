 var compareIds = [0, 0];
 var rtot_graph = null;
 var online_errors_rate_graph, compare_actions_response_times_graph, compare_cpu_load_graph = null;
 var monitoring_graph, overall_graph = null;
 var current_project_name = "";
 var min_slider_value, max_slider_value = 0;
 var action = "";

 var select_monitoring_server, select_monitoring_metric = "";
 var select_monitoring_compare_metric = "";
 var select_monitoring_compare_servers = ["", ""]
 var getUrlParameter = function getUrlParameter(sParam) {
     var sPageURL = decodeURIComponent(window.location.search.substring(1)),
         sURLVariables = sPageURL.split('&'),
         sParameterName,
         i;

     for (i = 0; i < sURLVariables.length; i++) {
         sParameterName = sURLVariables[i].split('=');

         if (sParameterName[0] === sParam) {
             return sParameterName[1] === undefined ? true : sParameterName[1];
         }
     }
 };

 var draw_monitoring_graph = function draw_monitoring_graph(test_id, server, metric) {
     var unit = "";
     var max_y = 0;
     var max_metric_value = httpGet('?action=get_monitoring_data&sub_action=get_metric_max_value&test_id=' +
         test_id + "&server=" + server + "&metric=" + metric);
     console.log("max_metric_value:" + max_metric_value);
     if (metric.indexOf("CPU") > -1) {
         unit = " %";
         max_y = Math.round(max_metric_value);
     } else if (metric.indexOf("Memory") > -1) {
         max_y = Math.round(max_metric_value + max_metric_value * 0.1);
         unit = " Mb";
     } else {
         max_y = Math.round(max_metric_value + max_metric_value * 0.1);
     }
     console.log("max_y:" + max_y);

     var max_rps_value = httpGet('?action=get_monitoring_data&sub_action=get_metric_max_value&test_id=' +
              test_id + "&server=" + server + "&metric=RPS");
     max_y2 = Math.round(max_rps_value);
     max_y2 = max_y2*1.2;
     monitoring_graph = c3.generate({
         data: {
             url: '?action=get_monitoring_data&sub_action=get_metric_data&test_id=' + test_id + "&server=" + server +
                 "&metric=" + metric,
             type: 'line',
             x: 'timestamp',
             xFormat: '%H:%M:%S',
             axes: {
                                                  rps: 'y2'
                                              },
         },
         axis: {
             x: {
                 type: 'timeseries',
                 tick: {
                     format: '%H:%M:%S'
                 }
             },
             y: {
                 max: max_y,
                 min: 0,
                 padding: {
                     top: 0,
                     bottom: 0
                 },
                 label: metric + " (" + unit + ")",
             },
             y2: {
                 min: 0,
                 show: true,
                 max: max_y2,
                 padding: {
                 top: 0,
                 bottom: 0
                 },
                 label: 'Requests/s',
                 }

         },
         title: {
             text: metric + ' on ' + server
         },
         bindto: '#placeformonitoringgraph'
     });
     /* setTimeout(function() {
      monitoring_graph.load({
                          url: '?action=get_test_data&sub_action=get_rps&test_id=' + test_id,
                          type: 'line',
                      });
      }, 500);*/
     updateElements();

 }

 var draw_monitoring_compare_graph = function draw_monitoring_compare_graph(test_ids, servers, metric) {
 var unit = "";
 var max_y = 0;
 var max_metric_value = httpGet('?action=get_monitoring_data&sub_action=get_metric_max_value&test_id=' +
         test_ids[0] + "&server=" + servers[0] + "&metric=" + metric);
 if (metric.indexOf("CPU") > -1) {
          unit = " %";
          max_y = Math.round(max_metric_value);
      } else if (metric.indexOf("Memory") > -1) {
          max_y = Math.round(max_metric_value + max_metric_value * 0.1);
          unit = " Mb";
      } else {
          max_y = Math.round(max_metric_value + max_metric_value * 0.1);
      }
    compare_monitoring_data_graph = c3.generate({
             data: {
                 url: '?action=get_monitoring_data&sub_action=get_metric_compare_data&test_ids=' + test_ids + "&servers=" + servers +
                     "&metric=" + metric,
                 type: 'line',
                 x: 'timestamp',
                 xFormat: '%H:%M:%S',
             },
             axis: {
                 x: {
                     type: 'timeseries',
                     tick: {
                         format: '%H:%M:%S'
                     }
                 },
                 y: {
                     max: max_y,
                     min: 0,
                     padding: {
                         top: 0,
                         bottom: 0
                     },
                     label: metric + " (" + unit + ")",
                 },

             },
             title: {
                 text: metric + ' on ' + servers
             },
             bindto: '#compare_monitoring_data_graph'
         });
         updateElements();

 }

 function httpGet(theUrl) {
     var xmlHttp = new XMLHttpRequest();
     xmlHttp.open("GET", theUrl, false); // false for synchronous request
     xmlHttp.send(null);
     return xmlHttp.responseText;
 }

 function httpPost(theUrl, request) {
     var xmlHttp = new XMLHttpRequest();
     xmlHttp.open("POST", theUrl, false); // false for synchronous request
     xmlHttp.send(request);
     return xmlHttp.responseText;
 }


 function updateElements() {

     $("#tabs").tabs({
         activate: function(event, ui) {
             //console.log(event);
             if (ui.newTab.find("a").attr("href") == "#online_tab") {

                 var response = httpGet("/getonlinedata?action=getrunningtestslist");
                 document.getElementById("online_tab").innerHTML = response;

                 $("#select-choice-runningtests").selectmenu({
                     change: function(event, ui) {
                         var runningtest_id = ui.item.value;
                         response = httpGet("/getonlinedata?action=get_online_page");
                         document.getElementById("online_tab_body").innerHTML = response;
                         var update_data = httpGet('/getonlinedata?action=update&runningtest_id=' + runningtest_id);

                         $("#tabs_online_data").tabs().addClass('tabs');
                         var online_graph = c3.generate({
                             data: {
                                 url: '/getonlinedata?action=get_running_test_rtot_data&runningtest_id=' + runningtest_id,
                                 filter: function(d) {
                                     return (d.id !== 'count' && d.id !== 'errors_count');
                                 },
                                 type: 'line',
                                 x: 'time',
                                 xFormat: '%Y-%m-%d %H:%M:%S',
                                 axes: {
                                     rps: 'y2'
                                 },
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
                                     label: 'Response times (ms)',
                                 },
                                 y2: {
                                     min: 0,
                                     show: true,
                                     padding: {
                                         top: 0,
                                         bottom: 0
                                     },
                                     label: 'Requests/s',
                                 }

                             },
                             bindto: '#online_graph'
                         });
                         successful_requests_percentage = httpGet('/getonlinedata?action=get_successful_requests_percentage&runningtest_id=' + runningtest_id);
                         console.log('successful_requests_percentage:' + successful_requests_percentage);
                         var online_successful_requests_percentage_graph = c3.generate({
                             size: {
                                 height: 400,
                                 width: 350
                             },
                             data: {
                                 columns: [
                                     ['Success_%', successful_requests_percentage]
                                 ],

                                 type: 'gauge',
                                 onclick: function(d, i) {},
                                 onmouseover: function(d, i) {},
                                 onmouseout: function(d, i) {}
                             },
                             color: {
                                 pattern: ['#FF0000', '#F6C600', '#60B044'], // the three color levels for the percentage values.
                                 threshold: {
                                     //            unit: 'value', // percentage is default
                                     //            max: 200, // 100 is default
                                     values: [97, 99, 100]
                                 }
                             },

                             title: {
                                 text: 'Successful requests percentage (%)'
                             },
                             bindto: '#online_successful_requests_percentage_graph'
                         });

                         rps = httpGet('/getonlinedata?action=get_rps&runningtest_id=' + runningtest_id);
                         console.log('rps:' + rps);
                         var online_rps_graph = c3.generate({
                             size: {
                                 height: 400,
                                 width: 350
                             },
                             data: {
                                 columns: [
                                     ['rps', rps]
                                 ],

                                 type: 'gauge',
                                 onclick: function(d, i) {},
                                 onmouseover: function(d, i) {},
                                 onmouseout: function(d, i) {}
                             },
                             gauge: {
                                 label: {
                                     format: function(value, ratio) {
                                         return value;
                                     },
                                     show: true // to turn off the min/max labels.
                                 },
                                 min: 0, // 0 is default, //can handle negative min e.g. vacuum / voltage / current flow / rate of change
                                 max: 500, // 100 is default
                                 units: ' rps',
                                 //    width: 39 // for adjusting arc thickness
                             },

                             title: {
                                 text: 'Requests per second (average during the last minute)'
                             },
                             bindto: '#online_rps_graph'
                         });
                         var online_response_codes_graph = c3.generate({
                             size: {
                                 height: 400,
                                 width: 350
                             },
                             data: {
                                 url: '/getonlinedata?action=get_response_codes&runningtest_id=' + runningtest_id,

                                 type: 'donut',
                                 onclick: function(d, i) {
                                     console.log("onclick", d, i);
                                 },
                                 onmouseover: function(d, i) {
                                     console.log("onmouseover", d, i);
                                 },
                                 onmouseout: function(d, i) {
                                     console.log("onmouseout", d, i);
                                 }
                             },
                             donut: {
                                 title: "Response codes"
                             },
                             bindto: '#online_response_codes_graph'
                         });


                         var onlineAggregateTable = httpGet('/getonlinedata?action=get_running_test_aggregate_data&runningtest_id=' + runningtest_id);
                         document.getElementById("online_aggregate_table").innerHTML = onlineAggregateTable;
                         //$('#online_aggregate').tablesorter();
                         setInterval(function() {
                             //onlineAggregateTable = httpGet('/getonlinedata?action=get_running_test_aggregate_data&runningtest_id=' + runningtest_id);
                             //document.getElementById("online_aggregate_table").innerHTML = onlineAggregateTable;

                             update_data = httpGet('/getonlinedata?action=update&runningtest_id=' + runningtest_id);
                             console.log(update_data);
                             online_graph.load({


                                 url: '/getonlinedata?action=get_running_test_rtot_data&runningtest_id=' + runningtest_id,
                                 filter: function(d) {
                                     return (d.id !== 'count' && d.id !== 'errors_count');
                                 },

                             });

                             online_response_codes_graph.load({

                                 url: '/getonlinedata?action=get_response_codes&runningtest_id=' + runningtest_id,
                             });
                             rps = httpGet('/getonlinedata?action=get_rps&runningtest_id=' + runningtest_id);
                             console.log('rps:' + rps);

                             online_rps_graph.load({


                                 columns: [
                                     ['rps', rps]
                                 ]

                             });
                             successful_requests_percentage = httpGet('/getonlinedata?action=get_successful_requests_percentage&runningtest_id=' + runningtest_id);
                             console.log('successful_requests_percentage:' + successful_requests_percentage);
                             online_successful_requests_percentage_graph.load({


                                 columns: [
                                     ['Success_%', successful_requests_percentage]
                                 ]

                             });



                         }, 5000);


                     }
                 });


             }
         }
     }).tabs({
         disabled: [3]
     }).addClass('tabs');
     $("#tabs_test_data").tabs().addClass('tabs');
     $("#tabs_compare_tests").tabs().addClass('tabs');
     $("#compare_tests_comparison_tables_tabs").tabs().addClass('tabs');




     $("#select-server-0").selectmenu({

         change: function(event, ui) {
             var server_name = ui.item.value;
             select_monitoring_server = server_name;
             if (select_monitoring_metric == "") select_monitoring_metric = "CPU_all";
             draw_monitoring_graph(compareIds[0], select_monitoring_server, select_monitoring_metric);
         }
     });
     $("#select-monitoring-metric").selectmenu({
         change: function(event, ui) {
             var monitoring_metric = ui.item.value;
             select_monitoring_metric = monitoring_metric;
             draw_monitoring_graph(compareIds[0], select_monitoring_server, select_monitoring_metric);
         }
     });

     $("#select-server-test-1").selectmenu({
         change: function(event, ui) {
             var server_name_1 = ui.item.value;
             select_monitoring_compare_servers[0] = server_name_1;
             if (select_monitoring_compare_metric == "") select_monitoring_compare_metric = "CPU_all";

             if (select_monitoring_compare_servers[0] != "" && select_monitoring_compare_servers[1] != "") {
                 draw_monitoring_compare_graph(compareIds, select_monitoring_compare_servers, select_monitoring_compare_metric);
             }
         }
     });
     $("#select-server-test-2").selectmenu({
         change: function(event, ui) {
             var server_name_2 = ui.item.value;
             select_monitoring_compare_servers[1] = server_name_2;
             if (select_monitoring_compare_metric == "") select_monitoring_compare_metric = "CPU_all";
             if (select_monitoring_compare_servers[0] != "" && select_monitoring_compare_servers[1] != "") {
                 draw_monitoring_compare_graph(compareIds, select_monitoring_compare_servers, select_monitoring_compare_metric);
             }
         }
     });
     $("#select-monitoring-compare-metric").selectmenu({
         change: function(event, ui) {
             var monitoring_metric = ui.item.value;
             select_monitoring_compare_metric = monitoring_metric;
             if (select_monitoring_compare_servers[0] != "" && select_monitoring_compare_servers[1] != "") {
                 draw_monitoring_compare_graph(compareIds, select_monitoring_compare_servers, select_monitoring_compare_metric);
             }
         }
     });


     $("#select-choice-project-overall").selectmenu({


         change: function(event, ui) {
             var project_name = ui.item.value;

             current_project_name = project_name;
             document.getElementById("ccc").innerHTML = '<hr/><div id="overall_project_graph"></div><div id="slider-range"></div>';

             min_slider_value = parseFloat(httpGet("/gettestslist?action=min_test_id&project_name=" + project_name));
             max_slider_value = parseFloat(httpGet("/gettestslist?action=max_test_id&project_name=" + project_name));

             console.log(min_slider_value);
             console.log(max_slider_value);

             overall_graph = c3.generate({
                 size: {
                     height: 400,
                 },
                 data: {
                     url: '/getoverallcomparedata?project_name=' + project_name + "&action=all_data",
                     filter: function(d) {
                         return (d.id !== 'Average' && d.id !== 'Median');
                     },
                     x: 'Release',
                     type: 'bar',
                     labels: true,
                     names: "cpu",
                     axes: {
                         Average: 'y2',
                         Median: 'y2'
                     },
                     labels: {
                         format: {
                             "Average": d3.format('.2f'),
                             "Median": d3.format('.2f')
                             //                data1: function (v, id, i, j) { rern "Format for data1"; },
                         }
                     },

                 },

                 legend: {
                     show: true,
                     position: 'inset',
                     inset: {
                         anchor: 'top-right',
                         x: undefined,
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
                         padding: {
                             top: 0,
                             bottom: 0
                         },
                         label: 'CPU load (%)',
                     },
                     y2: {
                         min: 0,
                         show: true,
                         padding: {
                             top: 0,
                             bottom: 0
                         },
                         label: 'Response time (ms)',
                     }
                 },
                 tooltip: {
                     format: {
                         value: function(value, ratio, id) {
                             var format = d3.format(".2f");
                             return format(value);
                         }
                         //            value: d3.format(',') // apply this format to both y and y2
                     }
                 },
                 title: {
                     text: 'Average response times (ms) and CPU load (%) on servers through all releases'
                 },
                 bindto: '#overall_project_graph'
             });
             setTimeout(function() {
                 overall_graph.load({

                     url: '/getoverallcomparedata?project_name=' + project_name + "&action=all_data",
                     filter: function(d) {
                         return (d.id === 'Average' || d.id === 'Median');
                     },
                     type: 'line',

                 });
             }, 1000);




             updateElements();
         }
     });


     $("#slider-range").slider({
         range: true,
         min: min_slider_value,
         max: max_slider_value,
         values: [min_slider_value, max_slider_value],
         change: function(event, ui) {
             $("#amount").val("$" + ui.values[0] + " - $" + ui.values[1]);
             console.log(ui.values[0]);
             console.log(ui.values[1]);

             overall_graph = c3.generate({
                 size: {
                     height: 400,
                 },
                 data: {
                     url: '/getoverallcomparedata?project_name=' + current_project_name + "&action=bounded_data&test_id_min=" + ui.values[0] + "&test_id_max=" + ui.values[1],
                     filter: function(d) {
                         return (d.id !== 'Average' && d.id !== 'Median');
                     },
                     x: 'Release',
                     type: 'bar',
                     labels: true,
                     names: "cpu",
                     axes: {
                         Average: 'y2',
                         Median: 'y2'
                     },
                     labels: {
                         format: {
                             "Average": d3.format('.2f'),
                             "Median": d3.format('.2f')
                             //                data1: function (v, id, i, j) { rern "Format for data1"; },
                         }
                     },

                 },

                 legend: {
                     show: true,
                     position: 'inset',
                     inset: {
                         anchor: 'top-right',
                         x: undefined,
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
                         padding: {
                             top: 0,
                             bottom: 0
                         },
                         label: 'CPU load (%)',
                     },
                     y2: {
                         min: 0,
                         show: true,
                         padding: {
                             top: 0,
                             bottom: 0
                         },
                         label: 'Response time (ms)',
                     }
                 },
                 tooltip: {
                     format: {
                         value: function(value, ratio, id) {
                             var format = d3.format(".2f");
                             return format(value);
                         }
                         //            value: d3.format(',') // apply this format to both y and y2
                     }
                 },
                 title: {
                     text: 'Average response times (ms) and CPU load (%) on servers through all releases'
                 },
                 bindto: '#overall_project_graph'
             });
             setTimeout(function() {
                 overall_graph.load({

                     url: '/getoverallcomparedata?project_name=' + current_project_name + "&action=bounded_data&test_id_min=" + ui.values[0] + "&test_id_max=" + ui.values[1],
                     filter: function(d) {
                         return (d.id === 'Average' || d.id === 'Median');
                     },
                     type: 'line',

                 });
             }, 1000);


         }
     });


     $("#select-choice-project-compare").selectmenu({
         width: 'auto',
         change: function(event, ui) {
             var project_name = ui.item.value;
             current_project_name = project_name;
             var response = httpGet("/gettestslist?action=fulllist&project_name=" + project_name);
             document.getElementById("placeforlist1").innerHTML = response;
             updateElements();
         }
     });
     $("#select-choice-2").selectmenu({

         change: function(event, ui) {
             var test_id = ui.item.value;
             if (test_id != 99999) {
                 var response = httpGet("/gettestdata?test_id=" + test_id);
                 document.getElementById("placefortable").innerHTML = response;
                 rtot_graph = c3.generate({
                                      data: {
                                          url: "/gettestrtotdata?test_id=" + test_id,
                                          type: 'line',
                                          x: 'timestamp',
                                          xFormat: '%H:%M:%S',
                 						 axes: {
                                                                   rps: 'y2'
                                                               },
                                      },
                                      zoom: {
                                                                   enabled: true
                                                               },
                                      axis: {
                                          x: {
                                  type: 'timeseries',
                                  tick: {
                                      format: '%H:%M:%S'
                 						}
                 						},
                                          y: {
                                              padding: {
                                                  top: 0,
                                                  bottom: 0
                                              },
                                              label: 'response times (ms)',
                                          },
                 						 y2: {
                                  min: 0,
                                  show: true,
                                  padding: {
                                  top: 0,
                                  bottom: 0
                                  },
                                  label: 'Requests/s',
                                  }

                                      },
                                      bindto: '#placeforgraph'
                                  });



                 updateElements();
                 compareIds[0] = ui.item.value;
             }
         }


     });
     $("#select-choice-3").selectmenu({

         change: function(event, ui) {
             var test_id = ui.item.value;
             if (test_id != 99999) {
                 var response = httpGet("/getaggregatedata/" + test_id);
                 var d = ""
                 compareIds[1] = ui.item.value;
                 if (compareIds[0] != 0 && compareIds[1] != 0) {
                     response = httpPost("/comparetests", JSON.stringify(compareIds));
                     rtot_graph = c3.generate({
                                          data: {
                                              url: "/gettestrtotdata?test_id=" + test_id,
                                              type: 'line',
                                              x: 'timestamp',
                                              xFormat: '%H:%M:%S',
                     						 axes: {
                                                                       rps: 'y2'
                                                                   },
                                          },
                                          zoom: {
                                                                       enabled: true
                                                                   },
                                          axis: {
                                              x: {
                                      type: 'timeseries',
                                      tick: {
                                          format: '%H:%M:%S'
                     						}
                     						},
                                              y: {
                                                  padding: {
                                                      top: 0,
                                                      bottom: 0
                                                  },
                                                  label: 'response times (ms)',
                                              },
                     						 y2: {
                                      min: 0,
                                      show: true,
                                      padding: {
                                      top: 0,
                                      bottom: 0
                                      },
                                      label: 'Requests/s',
                                      }

                                          },
                                          bindto: '#placeforgraph'
                                      });

                     var compare_actions_response_times_graph = c3.generate({
                         bindto: '#compare_actions_response_times_graph',
                         size: {
                             height: 700,
                         },
                         data: {
                             url: '/comparetestsdata?action=getactionscompareresponsetimes&test_id_1=' + compareIds[0] + '&test_id_2=' + compareIds[1], // specify that our above json is the data
                             x: 'URL', // specify that the "name" key is the x value
                             type: 'bar', // specfify type of plot
                             color: function(color, d) {
                                 if (d.value > 0) {
                                     return d3.rgb(d.value * 30, 0, 0);
                                 } else {
                                     return d3.rgb(0, Math.abs(d.value) * 20, 0);
                                 }
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
                             rotated: true, // horizontal bar chart
                             x: {
                                 type: 'category' // this needed to load string x value
                             },
                             y: {
                                 padding: {
                                     top: 0,
                                     bottom: 0
                                 },
                                 label: '%',
                                 max: 100,
                                 min: -100,
                             }
                         },
                         zoom: {
                             enabled: true
                         },
                         title: {
                             text: 'Difference of response times (%) between two tests (only > 1%)'
                         },
                         /*color: function (color, d) {
                     	       if(d.value>0)
                     	       {
                     	       return d3.rgb(0, d.value, 0);
                     	       }
                     	       else
                     	       {
                     	       return d3.rgb(abs(d.value), 0, 0);
                     	       }
                        }
                         color: function (color, d) {
                                    // d will be 'id' when called for legends

                                    return d3.rgb(0,0,0);
                                }*/
                     });


                     var compare_cpu_load_graph = c3.generate({
                         bindto: '#compare_cpu_load_graph',
                         data: {
                             url: '/comparetestsdata?action=getcpuloadcompare&test_id_1=' + compareIds[0] + '&test_id_2=' + compareIds[1], // specify that our above json is the data
                             x: 'server_name', // specify that the "name" key is the x value
                             type: 'bar', // specfify type of plot
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
                                 type: 'category' // this needed to load string x value
                             },
                             y: {
                                 padding: {
                                     top: 0,
                                     bottom: 0
                                 },
                                 label: '%',
                                 max: 100,
                                 min: 0,
                             }
                         },
                         zoom: {
                             enabled: true
                         },
                         title: {
                             text: 'Compare CPU utilization'
                         },
                         /*color: function (color, d) {
                                          	       if(d.value>0)
                                          	       {
                                          	       return d3.rgb(0, d.value, 0);
                                          	       }
                                          	       else
                                          	       {
                                          	       return d3.rgb(abs(d.value), 0, 0);
                                          	       }
                                             }
                                              color: function (color, d) {
                                                         // d will be 'id' when called for legends

                                                         return d3.rgb(0,0,0);
                                                     }*/
                     });
                     /*setTimeout(function () {
                                rtot_graph.load({
                                     url: '/getrtotdata/'+compareIds[1],
                                     type: 'line',
                                     x:'timestamp',
                                     xFormat: '%Y-%m-%d %H:%M:%S',
                                 });
                             }, 1000);*/
                 }



                 document.getElementById("placefortable").innerHTML = response;
                 updateElements()
             }
         }


     });

     $("#select-choice-runningtests").selectmenu(

     );

     $("#get_last_report_button").click(function() {
         var project_name = current_project_name;
         var test_id = httpGet('/gettestslist?action=lasttestid&project_name=' + project_name);
         var response = httpGet("/gettestdata?test_id=" + test_id);
         document.getElementById("placefortable").innerHTML = response;
         rtot_graph = c3.generate({
                              data: {
                                  url: "/gettestrtotdata?test_id=" + test_id,
                                  type: 'line',
                                  x: 'timestamp',
                                  xFormat: '%H:%M:%S',
         						 axes: {
                                                           rps: 'y2'
                                                       },
                              },
                              zoom: {
                                                           enabled: true
                                                       },
                              axis: {
                                  x: {
                          type: 'timeseries',
                          tick: {
                              format: '%H:%M:%S'
         						}
         						},
                                  y: {
                                      padding: {
                                          top: 0,
                                          bottom: 0
                                      },
                                      label: 'response times (ms)',
                                  },
         						 y2: {
                          min: 0,
                          show: true,
                          padding: {
                          top: 0,
                          bottom: 0
                          },
                          label: 'Requests/s',
                          }

                              },
                              bindto: '#placeforgraph'
                          });



         updateElements();
         compareIds[0] = test_id;
     });


     var tables = document.getElementsByTagName("table");
     for (var i = 0; i < tables.length; i++) {
         var el = tables[i];
         if (el.id) {

             $('#' + el.id).tablesorter({
                 theme: 'green',
                 widthFixed: true,
                 showProcessing: true,
                 headerTemplate: '{content} {icon}', // Add icon for various themes

                 widgets: ['zebra', 'stickyHeaders', 'filter'],

                 widgetOptions: {

                     // extra class name added to the sticky header row
                     stickyHeaders: '',
                     // number or jquery selector targeting the position:fixed element
                     stickyHeaders_offset: 0,
                     // added to table ID, if it exists
                     stickyHeaders_cloneId: '-sticky',
                     // trigger "resize" event on headers
                     stickyHeaders_addResizeEvent: true,
                     // if false and a caption exist, it won't be included in the sticky header
                     stickyHeaders_includeCaption: true,
                     // The zIndex of the stickyHeaders, allows the user to adjust this to their needs
                     stickyHeaders_zIndex: 2,
                     // jQuery selector or object to attach sticky header to
                     stickyHeaders_attachTo: null,
                     // jQuery selector or object to monitor horizontal scroll position (defaults: xScroll > attachTo > window)
                     stickyHeaders_xScroll: null,
                     // jQuery selector or object to monitor vertical scroll position (defaults: yScroll > attachTo > window)
                     stickyHeaders_yScroll: null,

                     // scroll table top into view after filtering
                     stickyHeaders_filteredToTop: true

                     // *** REMOVED jQuery UI theme due to adding an accordion on this demo page ***
                     // adding zebra striping, using content and default styles - the ui css removes the background from default
                     // even and odd class names included for this demo to allow switching themes
                     // , zebra   : ["ui-widget-content even", "ui-state-default odd"]
                     // use uitheme widget to apply defauly jquery ui (jui) class names
                     // see the uitheme demo for more details on how to change the class names
                     // , uitheme : 'jui'
                 }
             });

             /*if (el.id.indexOf("Table") !== -1) {
                 $('#' + el.id).tablesorter({
                         headers: {
                             2: {
                                 sorter: 'responsetimes'
                             },
                             4: {
                                 sorter: 'responsetimes'
                             }
                         }
                     }

                 );
             } else {
                 $('#' + el.id).tablesorter();
             }*/
         }
     }
     /*
     $.tablesorter.addParser({
          // set a unique id
          id: 'responsetimes',
          is: function(s) {
              // return false so this parser is not auto detected
              return false;
          },
          format: function(s) {
              // format your data for normalization
              return s.replace(/[+]?(\d+).(\d+) ms \(.+?\)/g, "$1.$2");
          },
          // set type, either numeric or text
          type: 'numeric'
      });*/

     /* $('body').progressTracker({

                      horPosition : 'bottom',
                      trackAllHeadlines: true,
                      scrollSpeed: 1200,
                      horTitles: true,
                      horTracker: true,
                      horStyle: 'beam',
                      horTitlesOffset: 'top',
                      horOnlyActiveTitle: false
                  });*/
 }



 $(document).ready(function() {
     updateElements()
     action = getUrlParameter('action');
     console.log("Incoming action: " + action);
     if (action == 'getlasttestdata') {
         var project_name = getUrlParameter('project_name');
         current_project_name = project_name;
         var response = httpGet("/gettestslist?action=fulllist&project_name=" + project_name);
         document.getElementById("placeforlist1").innerHTML = response;
         var test_id = httpGet('/gettestslist?action=lasttestid&project_name=' + project_name);
         response = httpGet("/gettestdata?test_id=" + test_id);

         document.getElementById("placefortable").innerHTML = response;
        rtot_graph = c3.generate({
                             data: {
                                 url: "/gettestrtotdata?test_id=" + test_id,
                                 type: 'line',
                                 x: 'timestamp',
                                 xFormat: '%H:%M:%S',
        						 axes: {
                                                          rps: 'y2'
                                                      },
                             },
                             zoom: {
                                                          enabled: true
                                                      },
                             axis: {
                                 x: {
                         type: 'timeseries',
                         tick: {
                             format: '%H:%M:%S'
        						}
        						},
                                 y: {
                                     padding: {
                                         top: 0,
                                         bottom: 0
                                     },
                                     label: 'response times (ms)',
                                 },
        						 y2: {
                         min: 0,
                         show: true,
                         padding: {
                         top: 0,
                         bottom: 0
                         },
                         label: 'Requests/s',
                         }

                             },
                             bindto: '#placeforgraph'
                         });
         var index = $('#tabs a[href="#compare_tab"]').parent().index();
         console.log(index);
         $('#tabs').tabs("option", "active", index);
         $('#select-choice-project-compare').val(project_name);
         $("#select-choice-project-compare option:contains(" + project_name + ")").attr('selected', 'selected');
         compareIds[0] = test_id;
     } else if (action == 'getprojectdata') {
         var project_name = getUrlParameter('project_name');
         current_project_name = project_name;
         var response = httpGet("/gettestslist?action=fulllist&project_name=" + project_name);
         document.getElementById("placeforlist1").innerHTML = response;
         var tab_index = $('#tabs a[href="#compare_tab"]').parent().index();
         $('#tabs').tabs("option", "active", tab_index);
         $('#select-choice-project-compare').val(project_name);
         $('#select-choice-project-compare').trigger('change');
     } else if (action == 'getbuilddata') {
         var project_name = getUrlParameter('project_name');
         var build_number = getUrlParameter('build_number');
         current_project_name = project_name;
         var response = httpGet("/gettestslist?action=fulllist&project_name=" + project_name);
         document.getElementById("placeforlist1").innerHTML = response;
         var test_id = httpGet('/gettestslist?action=gettestid&project_name=' + project_name + '&build_number=' + build_number);
         response = httpGet("/gettestdata?test_id=" + test_id);

         document.getElementById("placefortable").innerHTML = response;
        rtot_graph = c3.generate({
                             data: {
                                 url: "/gettestrtotdata?test_id=" + test_id,
                                 type: 'line',
                                 x: 'timestamp',
                                 xFormat: '%H:%M:%S',
        						 axes: {
                                                          rps: 'y2'
                                                      },
                             },
                             zoom: {
                                                          enabled: true
                                                      },
                             axis: {
                                 x: {
                         type: 'timeseries',
                         tick: {
                             format: '%H:%M:%S'
        						}
        						},
                                 y: {
                                     padding: {
                                         top: 0,
                                         bottom: 0
                                     },
                                     label: 'response times (ms)',
                                 },
        						 y2: {
                         min: 0,
                         show: true,
                         padding: {
                         top: 0,
                         bottom: 0
                         },
                         label: 'Requests/s',
                         }

                             },
                             bindto: '#placeforgraph'
                         });
         var index = $('#tabs a[href="#compare_tab"]').parent().index();
         console.log(index);
         $('#tabs').tabs("option", "active", index);
         $('#select-choice-project-compare').val(project_name);
         $("#select-choice-project-compare option:contains(" + project_name + ")").attr('selected', 'selected');
         compareIds[0] = test_id;
     }
     updateElements();
 });
