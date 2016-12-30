 var compareIds = [0, 0]
 var rtot_graph = null;
 var online_graph,online_errors_rate_graph, compare_actions_response_times_graph, compare_cpu_load_graph = null;
 var monitoring_graph, overall_graph = null;
 var current_project_name = "";
 var min_slider_value, max_slider_value = 0;

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

                         online_graph = c3.generate({
                             data: {
                                 url: '/getonlinedata?action=getrunningtestrtotdata&runningtest_id=' + runningtest_id,
                                 type: 'line',
                                 x: 'time',
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
                             bindto: '#online_graph'
                         });

                         online_errors_rate_graph = c3.generate({
                                                    size: {
                                                    		height: 400,
                                                    		width:	350
                                                    		},
                                                    	data: {
                                                    		url: '/getonlinedata?action=getrunningtesterrorsratedata&runningtest_id=' + runningtest_id,
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
                                                    	},bindto: '#online_errors_rate_graph'
                                                    	});


                         var response2 = httpGet('/getonlinedata?action=getrunningtestaggregatedata&runningtest_id=' + runningtest_id);
                         document.getElementById("online_aggregate_table").innerHTML = response2;
                         console.log(response2)
                     }
                 });
                 $("#tabs_online_data").tabs().addClass('tabs');

             }
         }
     }).tabs( { disabled: [3] } ).addClass('tabs');
     $("#tabs_test_data").tabs().addClass('tabs');
     $("#tabs_compare_tests").tabs().addClass('tabs');
     $("#compare_tests_comparison_tables_tabs").tabs().addClass('tabs');




     $("#select-server-0").selectmenu({

         change: function(event, ui) {
             var server_name = ui.item.value;

             monitoring_graph = c3.generate({
                 data: {
                     url: '/getmonitoringdata?test_id=' + compareIds[0] + "&server=" + server_name,
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
                         max: 100,
                         min: 0,
                         padding: {
                             top: 0,
                             bottom: 0
                         },
                         label: 'CPU load (%)',
                     },

                 },
                 title: {
                     text: 'CPU load (%) on ' + server_name
                 },
                 bindto: '#placeformonitoringgraph'
             });
             updateElements();
         }
     });
     $("#select-choice-project-overall").selectmenu({


         change: function(event, ui) {
             var project_name = ui.item.value;

             current_project_name = project_name;
             document.getElementById("ccc").innerHTML = '<div id="overall_project_graph"></div><div id="slider-range"></div>';

             min_slider_value = parseFloat(httpGet("/gettestslist?action=oldesttest&project_name=" + project_name));
             max_slider_value = parseFloat(httpGet("/gettestslist?action=newesttest&project_name=" + project_name));



             console.log(max_slider_value);
             overall_graph = c3.generate({
                 size: {
                     height: 400,
                 },
                 data: {
                     url: '/getoverallcomparedata?project_name=' + project_name + "&action=all_data",
                     filter: function (d) {
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
                             value: function (value, ratio, id) {
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
                     filter: function (d) {
                     				return (d.id === 'Average' || d.id === 'Median');
                     			},
                     type: 'line',

                 });
             }, 1000);







             updateElements();
         }
     });


     $( "#slider-range" ).slider({
           range: true,
           min: min_slider_value,
           max: max_slider_value,
           values: [ min_slider_value, max_slider_value ],
           change: function( event, ui ) {
             $( "#amount" ).val( "$" + ui.values[ 0 ] + " - $" + ui.values[ 1 ] );
             console.log(ui.values[ 0 ] );
             console.log(ui.values[ 1 ] );

             overall_graph = c3.generate({
                              size: {
                                  height: 400,
                              },
                              data: {
                                  url: '/getoverallcomparedata?project_name=' + current_project_name + "&action=time_limited_data&time_min=" + ui.values[ 0 ]  + "&time_max=" + ui.values[ 1 ] ,
                                  filter: function (d) {
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
                                          value: function (value, ratio, id) {
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

                                 url: '/getoverallcomparedata?project_name=' + current_project_name + "&action=time_limited_data&time_min=" + ui.values[ 0 ]  + "&time_max=" + ui.values[ 1 ] ,
                                           filter: function (d) {
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
                             url: '/comparertotdata/' + JSON.stringify(compareIds),
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
                         bindto: '#placeforgraph'
                     });

                     var compare_actions_response_times_graph = c3.generate({
                     	bindto: '#compare_actions_response_times_graph',
                     	size: {
                        		height: 700,
                        		},
                     	data: {
                     		url: '/comparetestsdata?action=getactionscompareresponsetimes&test_id_1='+compareIds[0]+'&test_id_2=' + compareIds[1],			// specify that our above json is the data
                     		x: 'URL',		 // specify that the "name" key is the x value
                     		type: 'bar',			// specfify type of plot
                     		color: function (color, d) {
                                                 	       if(d.value>0)
                                                 	       {
                                                 	       return d3.rgb(d.value*30, 0 , 0);
                                                 	       }
                                                 	       else
                                                 	       {
                                                 	       return d3.rgb(0, Math.abs(d.value)*20, 0);
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
                     		rotated: true,		 // horizontal bar chart
                     		x: {
                     			type: 'category'   // this needed to load string x value
                     		},
                     		y: {
                     			padding: {top:0, bottom:0},
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
                                          		url: '/comparetestsdata?action=getcpuloadcompare&test_id_1='+compareIds[0]+'&test_id_2=' + compareIds[1],			// specify that our above json is the data
                                          		x: 'server_name',		 // specify that the "name" key is the x value
                                          		type: 'bar',			// specfify type of plot
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
                                          			type: 'category'   // this needed to load string x value
                                          		},
                                          		y: {
                                          			padding: {top:0, bottom:0},
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
                     var test_id =  httpGet('/gettestslist?action=lasttestid&project_name=' + project_name);
                     var response = httpGet("/gettestdata?test_id=" + test_id);
                     document.getElementById("placefortable").innerHTML = response;
                     rtot_graph = c3.generate({
                         data: {
                             url: "/gettestrtotdata?test_id=" + test_id,
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
                         bindto: '#placeforgraph'
                     });



             updateElements();
             compareIds[0] = test_id;
     });


     var tables = document.getElementsByTagName("table");
    for (var i = 0; i < tables.length; i++) {
         var el = tables[i];

         console.log(el.id);

         if (el.id) {
             console.log(el.id);
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
 });