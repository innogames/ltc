var selected_project = "";
var selected_server_for_monitoring_data,
selected_monitoring_metric = "";
var test_id_1, test_id_2;
var num_of_tests_to_compare, top_requests = 0;
var running_test_id = 0;

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

function show_alert(message) {
    // TODO: add validation for additional vars
    var text = message['message']['text'];
    var alert_type = message['message']['type'];
    $('#alert_placeholder').append(
    '<div id="alertdiv" class="alert alert-' +  alert_type + '">'+
    '<a class="close" data-dismiss="alert">×</a><span>'+text+'</span></div></div>')
    setTimeout(function() {
      $("#alertdiv").remove();
    }, 4000);
  }

 function popitup(url) {
    newwindow=window.open(url,'{{title}}','height=600,width=1200');
    if (window.focus) {newwindow.focus()}
    return false;
}

function httpGet(theUrl) {
      var xmlHttp = new XMLHttpRequest();
      xmlHttp.open("GET", theUrl, false); // false for synchronous request
      xmlHttp.send(null);
      return xmlHttp.responseText;
}

function updateSelectList(id, url, label, text_tag, value_tag) {
 $.getJSON(url, function(json){
               //json = JSON.parse(json_string);
               $(id).empty();
               $(id).append($('<option disabled selected>').text(label).attr('value', label));
               $.each(json, function(i, obj){
                       $(id).append($('<option>').text(obj[text_tag]).attr('value', obj[value_tag]));
               });
               $(id).selectpicker('refresh');
});
}

function updateTestsSelectList(id, url, label, text_tag, value_tag) {
 console.log("updateTestsSelectList2");
 $.getJSON(url, function(json){
               //json = JSON.parse(json_string);
               $(id).empty();
               $(id).append($('<option disabled selected>').text(label).attr('value', label));
               $.each(json, function(i, obj){
                       console.log(obj["description"]);
                       $(id).append($('<option>').text(obj[text_tag]).attr('value', obj[value_tag]).attr('data-subtext', obj["description"]));
               });
               $(id).selectpicker('refresh');
});
}

function selectValueInList(id, value){
	// wait until select list has got values and then select value
	$(function() {
		 var checkExist = setInterval(function() {
		 if ($(id + ' option').filter(function(){ return $(this).val() == value; }).length) {	
			console.log(id + " => " + value);
			$(id + " option").each(function(i){
			console.log($(this).text() + " : " + $(this).val());
			if($(this).val() == value)
			{
				$(this).attr("selected", "selected");
				$(id).selectpicker('refresh');
				$(id).change();
				return;
			}
			});
			clearInterval(checkExist);
			}
		 }, 100); 
		 });
}


 function updateElements() {

 $("#main_tabs").tabs();
 $("#analyzer_tabs").tabs();
 $("#administrator_tabs").tabs();
 $.ajax({
                          url: "/analyzer/dashboard",
                          type: "get",
                          success: function(response) {
                            $("#dashboard_page").html(response);
                          },
                          error: function(xhr) {
                            //Do Something to handle error
                          }
                        });


 $.ajax({
                          url: "/controller/",
                          type: "get",
                          success: function(response) {
                            $("#controller_page").html(response);

                          },
                          error: function(xhr) {
                            //Do Something to handle error
                          }
                        });

 $.ajax({
                          url: "/administrator/",
                          type: "get",
                          success: function(response) {
                            $("#administrator_page").html(response);

                          },
                          error: function(xhr) {
                            //Do Something to handle error
                          }
                        });

 $('#select_project_menu').on('change', function(){
                selected_project = $(this).find("option:selected").val();
                $.ajax({
                         url: "/analyzer/history",
                         type: "get",
                         success: function(response) {
                           $("#history_project_page").html(response);
                         },
                         error: function(xhr) {
                           //Do Something to handle error
                         }
                       });

                   $.ajax({
                            url: "/analyzer/analyze",
                            type: "get",
                            success: function(response) {
                              $("#analyze_page").html(response);
                              console.log(response);

                            },
                            error: function(xhr) {
                              //Do Something to handle error
                            }
                   });
  $(window).trigger('resize');
 });

 $('#select_running_test').on('change', function(){
                running_test_id = $(this).find("option:selected").val();
                $.ajax({
                         url: "/online/"+running_test_id+"/online_page/",
                         type: "get",
                         success: function(response) {
                           update_data = httpGet('/online/' + running_test_id + '/update/');
                           console.log(update_data);
                           $("#online_page").html(response);
                         },
                         error: function(xhr) {
                           //Do Something to handle error
                         }
                       });
  $(window).trigger('resize');
 });
 updateSelectList('#select_project_menu', "/analyzer/projects_list", "Select project", "project_name", "id");
 updateSelectList('#select_running_test', "/online/tests_list", "Select running test", "project_name", "id");

 handleIncomingAction();
 };



$(document).on('click', '.panel-heading span.clickable', function (e) {
    var $this = $(this);
    if (!$this.hasClass('panel-collapsed')) {
        $this.parents('.panel').find('.panel-body').slideUp();
        $this.addClass('panel-collapsed');
        $this.find('i').removeClass('glyphicon-minus').addClass('glyphicon-plus');
    } else {
        $this.parents('.panel').find('.panel-body').slideDown();
        $this.removeClass('panel-collapsed');
        $this.find('i').removeClass('glyphicon-plus').addClass('glyphicon-minus');
    }
});
$(document).on('click', '.panel div.clickable', function (e) {
    var $this = $(this);
    if (!$this.hasClass('panel-collapsed')) {
        $this.parents('.panel').find('.panel-body').slideUp();
        $this.addClass('panel-collapsed');
        $this.find('i').removeClass('glyphicon-minus').addClass('glyphicon-plus');
    } else {
        $this.parents('.panel').find('.panel-body').slideDown();
        $this.removeClass('panel-collapsed');
        $this.find('i').removeClass('glyphicon-plus').addClass('glyphicon-minus');
    }
});

$(document).ready(function() {
    updateElements();
    updateTables();
    //$('.panel-heading span.clickable').click();
    //$('.panel div.clickable').click();
});


function updateTables() {
var tables = document.getElementsByTagName("table");
     for (var i = 0; i < tables.length; i++) {
         var el = tables[i];
         if (el.id) {
         console.log("update table style:" + el.id);
             $('#' + el.id).tablesorter({
                 theme: 'bootstrap',
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
}

 function testReport(test_id) {
             $('#main_tabs').tabs("option", "active", $('#main_tabs a[href="#analyzer"]').parent().index());
             $('#analyzer_tabs').tabs("option", "active", $('#analyzer_tabs a[href="#analyze"]').parent().index());
             var test_2 = JSON.parse(httpGet('/analyzer/test/'+ test_id +'/prev_test_id/'));
             test_id_2 = test_2[0].id
			 console.log("1");
             selectValueInList('#select_test_1', test_id);    
			 console.log("3");
}

//TO SUPPORT OLD REQUESTS
var handleIncomingAction = function handleIncomingAction(){
     action = getUrlParameter('action');
     if (action == 'getbuilddata') {
         var project_name = getUrlParameter('project_name');
		 var projects_list = JSON.parse(httpGet('/analyzer/projects_list'));
		 $.each(projects_list, function(i, obj){
			 //console.log(obj);
             if(obj['project_name']==project_name)
             {
             selected_project_id = obj['id']
             }
             });
			 
         var build_number = getUrlParameter('build_number');
		 selectValueInList('#select_project_menu', selected_project_id);      
         var test = JSON.parse(httpGet('/analyzer/project/' + selected_project_id + '/'+ build_number +'/test_info/'));
         test_id_1 = test[0].id;
         testReport(test_id_1);
     }
 };


