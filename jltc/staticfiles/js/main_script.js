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
        '<div id="alertdiv" class="alert alert-' + alert_type + '">' +
        '<a class="close" data-dismiss="alert">×</a><span>' + text + '</span></div></div>')
    setTimeout(function () {
        $("#alertdiv").remove();
    }, 4000);
}

function popitup(url) {
    newwindow = window.open(url, '{{title}}', 'height=600,width=1200');
    if (window.focus) {
        newwindow.focus()
    }
    return false;
}

function updateSelectList(id, url, label, text_tag, value_tag) {
    $.getJSON(url, function (json) {
        $(id).empty();
        if (text_tag) {
            $(id).append($('<option disabled selected>').text(label).attr('value', label));
        }
        $.each(json, function (i, obj) {
            $(id).append($('<option>').text(obj[text_tag]).attr('value', obj[value_tag]));
        });
        $(id).selectpicker('refresh');
    });
}

function updateTestsSelectList(id, url, label, text_tag, value_tag) {
    console.log("updateTestsSelectList2");
    $.getJSON(url, function (json) {
        //json = JSON.parse(json_string);
        $(id).empty();
        $(id).append($('<option disabled selected>').text(label).attr('value', label));
        $.each(json, function (i, obj) {
            $(id).append($('<option>').text(obj[text_tag]).attr('value', obj[value_tag]).attr('data-subtext', obj['description']+obj['parameters'][1]['THREAD_COUNT']));
        });
        $(id).selectpicker('refresh');
    });
}

function selectValueInList(id, value) {
    // wait until select list has got values and then select value
    $(function () {
        var checkExist = setInterval(function () {
            if ($(id + ' option').filter(function () {
                    return $(this).val() == value;
                }).length) {
                console.log(id + " => " + value);
                $(id + " option").each(function (i) {
                    console.log($(this).text() + " : " + $(this).val());
                    if ($(this).val() == value) {
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
        success: function (response) {
            $("#dashboard_page").html(response);
        },
        error: function (xhr) {
            //Do Something to handle error
        }
    });


    $.ajax({
        url: "/controller/",
        type: "get",
        success: function (response) {
            $("#controller_page").html(response);

        },
        error: function (xhr) {
            //Do Something to handle error
        }
    });

    $.ajax({
        url: "/administrator/",
        type: "get",
        success: function (response) {
            $("#administrator_page").html(response);

        },
        error: function (xhr) {
            //Do Something to handle error
        }
    });

    $('#select_running_test').on('change', function () {
        running_test_id = $(this).find("option:selected").val();
        $.ajax({
            url: "/online/" + running_test_id + "/online_page/",
            type: "get",
            success: function (response) {
                $.ajax({
                    url: "/online/" + running_test_id + "/update/",
                    type: "get",
                    success: function (response) {
                    },
                    error: function (xhr) {
                    }
                });
                $("#online_page").html(response);
            },
            error: function (xhr) {
            }
        });
        $(window).trigger('resize');
    });
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

$(document).ready(function () {
    updateElements();
    updateTables();
});


function updateTables() {
    var tables = document.getElementsByTagName("table");
    for (var i = 0; i < tables.length; i++) {
        var el = tables[i];
        if (el.id) {
            $('#' + el.id).tablesorter({
                theme: 'bootstrap',
                widthFixed: true,
                showProcessing: true,
                headerTemplate: '{content} {icon}', // Add icon for various themes
                widgets: ['zebra', 'stickyHeaders', 'filter'],
                widgetOptions: {
                    stickyHeaders: '',
                    stickyHeaders_offset: 0,
                    stickyHeaders_cloneId: '-sticky',
                    stickyHeaders_addResizeEvent: true,
                    stickyHeaders_includeCaption: true,
                    stickyHeaders_zIndex: 2,
                    stickyHeaders_attachTo: null,
                    stickyHeaders_xScroll: null,
                    stickyHeaders_yScroll: null,
                    stickyHeaders_filteredToTop: true
                }
            });
        }
    }
}

function testReport(test_id) {
    $('#main_tabs').tabs("option", "active", $('#main_tabs a[href="#analyzer"]').parent().index());
    $('#analyzer_tabs').tabs("option", "active", $('#analyzer_tabs a[href="#analyze"]').parent().index());
    $.getJSON('/analyzer/test/' + test_id + '/prev_test_id/',
    function(json) {
        test_id_2 = json[0].id
    });
    selectValueInList('#select_test_1', test_id);
}

//TO SUPPORT OLD REQUESTS
var handleIncomingAction = function handleIncomingAction() {
    action = getUrlParameter('action');
    if (action == 'getbuilddata') {
        var project_name = getUrlParameter('project_name');
        $.getJSON('/analyzer/projects_list',
        function(json) {
            $.each(json, function(i, obj) {
                if (obj['project_name'] == project_name) {
                    selected_project_id = obj['id']
                    var build_number = getUrlParameter('build_number');
                    selectValueInList('#analyzer-select-project', selected_project_id);
                    $.getJSON('/analyzer/project/' + selected_project_id + '/' + build_number + '/test_info/',
                    function(json) {
                        testReport(json[0].id);
                    });
                }
            });
        });
    }
};