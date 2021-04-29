$("#dashboard_tabs").tabs();
var graphs = [];

function drawProjectOverallGraph(projectId) {
    graphs['overall_graph_' + projectId] = c3.generate({
        size: {
            height: 200,
        },
        data: {
            url: '/analyzer/project/' + projectId + '/project_history/',
            mimeType: 'json',
            keys: {
                x: 'test_name',
                value: ['mean', 'median'],
            },
            type: 'bar',

        },
        axis: {
            x: {
                type: 'category',
            },
            y: {
                max: 500,
                padding: {
                    top: 0,
                    bottom: 0
                },
                label: 'response times (ms)',
            },
        },
        zoom: {
            enabled: true
        },
        legend: {
            position: 'right'
        },
        bindto: '#overall_' + projectId
    });
}

function updateLoadGeneratorsTable() {
    $.ajax({
        url: '/controller/load_generators/get_data/',
        async: 'true',
        type: 'get',
        success: function (response) {
            $("#load_generators_list").empty();
            var loadgenerators_table = '<div class="table-responsive"><table class="table">' +
                '<thead>' +
                '<tr>' +
                '<th>Host</th>' +
                '<th>Free memory</th>' +
                '<th>Load</th>' +
                '<th>Jmeter Instances</th>' +
                '<th>Status</th>' +
                '</tr>' +
                '</thead>'
            $.each(response, function (i, obj) {
                var host_id = obj['id'];
                var hostname = obj['hostname'];
                var status = obj['status'];
                var reason = obj['reason'];
                var memory_free = obj['memory_free'];
                var jmeter_instances_count = obj['jmeter_instances_count'];
                var jmeter_instances_label = "info"
                if (jmeter_instances_count >= 5) jmeter_instances_label = "danger";
                else if (jmeter_instances_count < 5 && jmeter_instances_count > 2) jmeter_instances_label = "warning";
                var load = obj['la_5'];
                loadgenerators_table += '<tr><td><a href="/controller/load_generator/' + host_id + '/get_data/" onclick="return popitup(\'/controller/load_generator/' + host_id + '/get_data/\')">' + hostname + '</a></td>' + '<td>' + memory_free + '</td>' + '<td>' + load + '</td>' + '<td><span class="label label-' + jmeter_instances_label + '">' + jmeter_instances_count + '</span></td>' + '<td><span class="label label-' + status + '">' + reason + '</span></td></tr>';
            });
            loadgenerators_table += '</table></div>';
            $("#load_generators_list").append(loadgenerators_table);
        },
        error: function (xhr) {}
    });
}

function updateRunningTestsTable() {
    $.ajax({
        url: '/controller/running_tests/get_data/',
        async: 'true',
        type: 'get',
        success: function (response) {
            $("#running_tests_list").empty();
            var running_tests_table = '<div class="table-responsive"><table class="table">' +
                '<thead>' +
                '<tr>' +
                '<th>Project</th>' +
                '<th>Test ID</th>' +
                //'<th>Remote instances</th>' +
                '<th>Progress</th>' +
                '</tr>' +
                '</thead>'
            $.each(response, function (i, obj) {
                var project_name = obj['project_name'];
                var start_time = obj['start_time'];
                var current_time = obj['current_time'];
                var duration = obj['duration'];
                var id = obj['id'];
                var jmeter_remote_instances = obj['jmeter_remote_instances'];

                var progress = Math.round(((current_time - start_time) / 1000) * 100 / duration)
                if (progress > 100) progress = 100;
                var progress_bar = '<div class="progress">' +
                    '<div class="progress-bar progress-bar-striped active" role="progressbar"' +
                    'aria-valuenow="' + progress + '" aria-valuemin="0" aria-valuemax="100" style="width:' + progress + '%">' +
                    progress + '%' +
                    '</div></div>'
                running_tests_table += '<tr><td>' + project_name + '</td>' + '<td>' + id + '</td>' + '<td>' + progress_bar + '</td></tr>';
            });
            running_tests_table += '</table></div>';
            $("#running_tests_list").append(running_tests_table);
        },
        error: function (xhr) {}
    });
}
updateLoadGeneratorsTable();
updateRunningTestsTable();
setInterval(function () {
    updateLoadGeneratorsTable();
    updateRunningTestsTable();
}, 10000);