var csrf = $('#page-data').data('csrf');

class Test {
    constructor(id) {
        this.id = id;
        this.data = []
        this.dataOverTime = []
        this.aggregateTable = {}
        this.responseCodes = {}
        this.requestsCountData = {}
        this.startTime = 0
    }

    setId (id) {
        this.id = id
    }

    init()
    {
        this.refresh()
    }

    refresh() {
        $.ajax({
            url: `/api/v1/test/${this.id}`,
            type: 'get',
            context: this,
            success: function (response) {
                this.setData(response['online_data']);
            },
            error: function (xhr) {
                //Do Something to handle error
            }
        });
    }

    setData(data) {
        this.data = data;
        this.dataOverTime = data.filter(d => d.name === 'data_over_time')
        this.responseCodes = data.filter(d => d.name === 'response_codes')[0]
        this.aggregateTable = data.filter(d => d.name === 'aggregate_table')[0]
    }
}

class OnlineElement {
    constructor(id, data) {
        this.id = id;
        this.data = data;
    }
}

class OnlineGraph extends OnlineElement {
    constructor(id, data, description, title) {
        super(id, data);
        this.title = title;
        this.description = description;
        this.chart;
    }

    show() {
        this.description['data']['json'] = this.data;
        this.description['data']['mimeType'] = 'json';
        this.description['bindto'] = `#${this.id}`;
        this.description['title'] = {
            'text': this.title
        };
        this.chart = bb.generate(this.description)
    }

    update(data) {
        this.chart.load({
            json: data,
            mimeType: 'json'
        })
    }
}

class Online {
    constructor(test) {
        this.test = test;
        this.charts = new Array();
    }

    init() {
        this.initElements()
    }

    initElements() {
        this.test.refresh()
        this.charts = [
            new OnlineGraph('online_rtot',
                this.test.dataOverTime.map(function (r) {
                    return {
                        timestamp: new Date(r.data.timestamp),
                        avg: r.data.avg,
                        errors: r.data.errors / 60,
                        rps: r.data.count / 60
                    };
                }), {
                    data: {
                        type: 'line',
                        keys: {
                            x: 'timestamp',
                            value: ['avg', 'errors', 'rps'],
                        },
                        xFormat: '%Y-%m-%dT%H:%M:%S.%LZ',
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
                            min: 0,
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
                }, 'Response times over time graph'
            ),
        ]
        this.charts.forEach(
            function (chart, elementId) {
                chart.show();
            }
        )
    }

    renderAggregateTable() {
        let aggregate_table_html =
            `<table class="table table-striped table-bordered table-hover">
                <thead>
                    <tr>
                        <th>Action</th>
                        <th>Average</th>
                        <th>Count</th>
                        <th>Errors</th>
                        <th>Maximum</th>
                        <th>Minimum</th>
                        <th>Weight</th>
                    </tr>
                </thead>
                <tbody>`
        for (const [ k, v ] of Object.entries(this.test.aggregateTable.data)) {
            aggregate_table_html += `<tr>
                <td>${k}</td>
                <td>${v['average']}</td>
                <td>${v['count']}</td>
                <td>${v['errors']}</td>
                <td>${v['maximum']}</td>
                <td>${v['minimum']}</td>
                <td>${v['weight']}</td>
            </tr>`
        }
        aggregate_table_html += `</tbody></table>`
        $('#online_aggregate_table').html(aggregate_table_html);
        $("#online_aggregate_table").tablesorter();
        $("#online_aggregate_table").trigger('tsUpdate');
    }

    refresh(){
        var test = this.test
        test.refresh()
        this.renderAggregateTable()
        this.charts.forEach(
            function (chart, elementId) {
                if(chart.id == 'online_rtot' )
                {
                    chart.update(test.dataOverTime.map(function (r) {
                        return {
                            timestamp: new Date(r.data.timestamp),
                            avg: r.data.avg,
                            errors: r.data.errors / 60,
                            rps: r.data.count / 60
                        };
                    }));
                }
            }
        )
    }
}

$('#online_select_test').change(function () {
    var test = new Test($(this).val())
    var online = new Online(test);
    online.init();
    setInterval(function () {
        online.refresh()
    }, 5000);
})
