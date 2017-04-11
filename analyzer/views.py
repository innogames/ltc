from collections import OrderedDict
import json
import pandas as pd
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import TemplateView
from models import Project, Test, Aggregate, Server, TestData,\
    ServerMonitoringData, TestActionData, Action
from django.db.models import Sum, Avg, Max, Min, FloatField
from django.db.models.expressions import RawSQL, F
from decimal import Decimal

def to_dict(result_proxy):
    fieldnames = []
    for fieldname in result_proxy.keys():
        fieldnames.append(fieldname)
    results = []
    for row in result_proxy.fetchall():
        results.append(OrderedDict(zip(fieldnames, row)))
    return results


def to_json(result_proxy, as_object):
    results = to_dict(result_proxy)
    if as_object:
        json_object = json.loads(json.dumps(results , sort_keys=False),object_pairs_hook=OrderedDict)
        return json_object
    else:
        json_string = json.dumps(results, sort_keys=False,default=str,indent=4)
        return json_string


def to_pivot(data, a, b, c):
    df = pd.DataFrame(data)
    df_pivot = pd.pivot_table(df, index = a, columns = b, values = c)
    return df_pivot



def projects_list(request):
    #project_list = Project.objects.values('project_name')
    project_list = Project.objects.values()
    return JsonResponse(list(project_list),
                        safe=False)


def tests_list(request, project_id):
    t = Test.objects.filter(project__id=project_id).values().\
        order_by('-start_time')
    return JsonResponse(list(t), safe=False)


def last_test(request, project_id):
    t = Test.objects.filter(project__id=project_id)\
        .order_by('-start_time').values()
    return JsonResponse([list(t)[0]]
                        , safe=False)


def project_history(request, project_id):
    a = Aggregate.objects.annotate(test_name=F('test__display_name'))\
        .filter(test__project__id=project_id)\
        .values('test_name')\
        .annotate(Average=Avg('average')) \
        .annotate(Median=Avg('median')) \
        .order_by('-test__start_time')
    return JsonResponse(list(a), safe=False)


def test_info(request, project_id, build_number):
    t = Test.objects.filter(project__id=project_id,
                            build_number=build_number).values()
    return JsonResponse(list(t)
                        , safe=False)


def test_info_from_id(request, test_id):
    t = Test.objects.filter(id=test_id).values()
    return JsonResponse(list(t)
                        , safe=False)


def prev_test_id(request, test_id):
    p = Project.objects.\
        filter(test__id=test_id)
    start_time = Test.objects.filter(id=test_id).values('start_time')[0]['start_time']
    t = Test.objects.filter(start_time__lte=start_time,project=p).\
        values('id').order_by('-start_time')
    #data = db.get_prev_test_id(test_id, 2)
    return JsonResponse([list(t)[1]], safe=False)


def test_report(request, test_id):
    test_description = Test.objects.filter(id=test_id).values()
    aggregate_table = Aggregate.objects.\
        annotate(url=F('action__url'))\
        .filter(test_id=test_id). \
        values('url',
               'action_id',
               'average',
               'median',
               'weight',
               'percentile_75',
               'percentile_90',
               'percentile_99',
               'maximum',
               'minimum',
               'count',
               'errors')

    return render(request, 'report.html',
                  {'test_description': test_description[0],
                   'aggregate_table': aggregate_table})


def action_report(request, test_id, action_id):
    return render(request, 'url_report.html',
                  {'test_id': test_id,
                   'action': Action.objects.get(id=action_id)})


def action_rtot(request, test_id, action_id):
    min_timestamp = TestActionData.objects. \
        filter(test_id=test_id, action_id=action_id). \
        values("test_id", "action_id"). \
        aggregate(min_timestamp=Min(RawSQL("((data->>%s)::timestamp)", ('timestamp',))))['min_timestamp']
    x = TestActionData.objects. \
        filter(test_id=test_id, action_id=action_id). \
        annotate(timestamp=(RawSQL("((data->>%s)::timestamp)", ('timestamp',))-min_timestamp)). \
        annotate(average=RawSQL("((data->>%s)::numeric)", ('avg',))). \
        annotate(median=RawSQL("((data->>%s)::numeric)", ('median',))). \
        annotate(rps=(RawSQL("((data->>%s)::numeric)", ('count',)))/60). \
        annotate(errors=(RawSQL("((data->>%s)::numeric)", ('errors',)))/60). \
        values('timestamp', "average", "median", "rps","errors"). \
        order_by('timestamp')
    data = json.loads(json.dumps(list(x), indent=4, sort_keys=True, default=str))
    return JsonResponse(data, safe=False)


def available_test_monitoring_metrics(request, test_id, server_id):
    x = ServerMonitoringData.objects.\
        filter(test_id = test_id, server_id = server_id).values('data')[:1]
    data = list(x)[0]["data"]
    metrics = []
    for value in data:
        if "test_id" not in value and "timestamp" not in value:
            metrics.append({"metric": value})
    metrics.append({"metric":"CPU_all"})
    return JsonResponse(metrics, safe=False)


def test_servers(request, test_id):
    servers_list = Server.objects.\
        filter(servermonitoringdata__test_id=test_id).\
        values().distinct()

    return JsonResponse(list(servers_list), safe=False)


def compare_tests_cpu(request, test_id, num_of_tests):
    project = Test.objects.filter(id=test_id).values('project_id')
    project_id = project[0]['project_id']
    start_time = Test.objects.filter(id=test_id).values('start_time')[0]['start_time']
    data = (ServerMonitoringData.objects.\
        filter(test__start_time__lte=start_time, test__project_id=project_id). \
        values('test__display_name', 'server__server_name','test__start_time'). \
        annotate(cpu_load=RawSQL("((data->>%s)::float)+((data->>%s)::float)+((data->>%s)::float)",
                            ('CPU_user','CPU_iowait','CPU_system',))). \
        annotate(cpu_load=Avg('cpu_load')).order_by('-test__start_time'))
    #FUCK YOU DJANGO ORM >_<. DENSE_RANK does not work so:
    current_rank = 1
    counter = 0
    arr = []
    for d in data:
        if counter < 1:
            d['rank'] = current_rank
        else:
            if int(d['test__start_time']) == int(data[counter-1]['test__start_time']):
                d['rank'] = current_rank
            else:
                current_rank += 1
                d['rank'] = current_rank
        # filter by rank >_<
        if int(d['rank']) <= int(num_of_tests) + 1:
            # C3.js does not accept "."
            d['server__server_name'] = d['server__server_name'].\
                replace(".","_")
            arr.append(d)
        counter += 1
    response = list(arr)
    response = to_pivot(response, 'test__display_name', 'server__server_name', 'cpu_load')
    response = response.to_json(orient='index')
    #return HttpResponse(response)
    return HttpResponse(
        json.loads(json.dumps(response , sort_keys=False),
                   object_pairs_hook=OrderedDict))


def compare_tests_avg(request, test_id, num_of_tests):
    project = Test.objects.filter(id=test_id).values('project_id')
    start_time = Test.objects.filter(id=test_id).values('start_time')[0]['start_time']
    project_id = project[0]['project_id']

    data = Aggregate.objects. \
        annotate(display_name=F('test__display_name')). \
        annotate(start_time=F('test__start_time')). \
        filter(test__start_time__lte=start_time, test__project_id=project_id).\
        values('display_name','start_time'). \
        annotate(average=Avg('average')). \
        annotate(median=Avg('median')). \
        order_by('-test__start_time')
    current_rank = 1
    counter = 0
    arr = []
    for d in data:
        if counter < 1:
            d['rank'] = current_rank
        else:
            if int(d['start_time']) == int(data[counter-1]['start_time']):
                d['rank'] = current_rank
            else:
                current_rank += 1
                d['rank'] = current_rank
        # filter by rank >_<
        if int(d['rank']) <= int(num_of_tests) + 1:
            arr.append(d)
        counter += 1
    response = list(arr)
    return JsonResponse(response, safe=False)


def test_rtot(request, test_id):
    min_timestamp = TestData.objects. \
        filter(test_id=test_id). \
        values("test_id").\
        aggregate(min_timestamp=Min(RawSQL("((data->>%s)::timestamp)", ('timestamp',))))['min_timestamp']
    x = TestData.objects. \
        filter(test_id=test_id). \
        annotate(timestamp=(RawSQL("((data->>%s)::timestamp)", ('timestamp',))-min_timestamp)). \
        annotate(average=RawSQL("((data->>%s)::numeric)", ('avg',))). \
        annotate(median=RawSQL("((data->>%s)::numeric)", ('median',))). \
        annotate(rps=(RawSQL("((data->>%s)::numeric)", ('count',)))/60). \
        values('timestamp', "average", "median", "rps"). \
        order_by('timestamp')
    data = json.loads(json.dumps(list(x), indent=4, sort_keys=True, default=str))
    return JsonResponse(data, safe=False)


def test_errors(request, test_id):
    value = Aggregate.objects.filter(test_id=test_id)\
        .values('test_id'). \
        annotate(errors_percentage=100*Sum(F("count")*F("errors")/100, output_field=FloatField())
                                    * Decimal('1.0')/Sum(F('count'), output_field=FloatField()))
    errors_percentage = float(list(value)[0]['errors_percentage'])
    response = [{"fail_%": errors_percentage,
                 "success_%": 100-errors_percentage}]
    return JsonResponse(response, safe=False)


def test_top_avg(request, test_id, top_number):
    data = Aggregate.objects.annotate(url=F('action__url')).filter(test_id=test_id) \
        .order_by('-average').values('url','average')[:top_number]
    return JsonResponse(list(data), safe=False)


def test_top_errors(request, test_id):
    data = Aggregate.objects.annotate(url=F('action__url')).filter(test_id=test_id) \
               .order_by('-errors').values('url','action_id','errors')[:5]
    return JsonResponse(list(data), safe=False)


def metric_max_value(request, test_id, server_id, metric):
    max_value = {}
    if 'CPU' in metric:
        max_value = {'max_value': 100}
    else:
        max_value = ServerMonitoringData.objects. \
        filter(test_id=test_id, server_id=server_id).\
        annotate(val=RawSQL("((data->>%s)::numeric)", (metric,))).\
        aggregate(max_value=Max('val', output_field=FloatField()))
    return JsonResponse(max_value, safe=False)


def tests_compare_aggregate(request, test_id_1, test_id_2):
    data = Aggregate.objects.raw(
        """
        SELECT a.url as "id", a1.average as "average_1", a2.average as "average_2", a1.average - a2.average as "avg_diff",
        (((a1.average-a2.average)/a2.average)*100) as "avg_diff_percent",
        a1.median - a2.median as "median_diff",
        (((a1.median-a2.median)/a2.median)*100) as "median_diff_percent" FROM
        (SELECT action_id, average, median FROM jltom.aggregate WHERE test_id = %s) a1,
        (SELECT action_id, average, median FROM jltom.aggregate WHERE test_id = %s) a2,
        jltom.action a
        WHERE a1.action_id = a2.action_id and a.id = a1.action_id
        """, [test_id_1, test_id_2])
    response = []
    for row in data:
        response.append({"url": row.id, "average_1": row.average_1,
                         "average_2": row.average_2,
                         "avg_diff": row.avg_diff,
                         "avg_diff_percent": row.avg_diff_percent,
                         "median_diff": row.median_diff,
                         "median_diff_percent": row.median_diff_percent
                         })
    return JsonResponse(response, safe=False)


def metric_data(request, test_id, server_id, metric):
    min_timestamp = ServerMonitoringData.objects. \
        filter(test_id=test_id). \
        values("test_id"). \
        aggregate(min_timestamp=Min(RawSQL("((data->>%s)::timestamp)", ('timestamp',))))['min_timestamp']

    if metric == 'CPU_all':
        metric_mapping = {
            metric: RawSQL("(((data->>%s)::numeric)+((data->>%s)::numeric)+((data->>%s)::numeric))",
                           ('CPU_iowait','CPU_user','CPU_system',))
        }
    else:
        metric_mapping = {
            metric: RawSQL("((data->>%s)::numeric)", (metric,))
        }
    x = ServerMonitoringData.objects. \
        filter(test_id=test_id, server_id=server_id). \
        annotate(timestamp=RawSQL("((data->>%s)::timestamp)", ('timestamp',))-min_timestamp).\
        annotate(**metric_mapping). \
        values('timestamp', metric)
    #annotate(metric=RawSQL("((data->>%s)::numeric)", (metric,)))
    data = json.loads(json.dumps(list(x), indent=4, sort_keys=True, default=str))
    return JsonResponse(data, safe=False)


def tests_compare_report(request, test_id_1, test_id_2):
    data = Aggregate.objects.raw(
        """
        SELECT a.url as "id", a1.average as "average_1", a2.average as "average_2", a1.average - a2.average as "avg_diff",
        (((a1.average-a2.average)/a2.average)*100) as "avg_diff_percent",
        a1.median - a2.median as "median_diff",
        (((a1.median-a2.median)/a2.median)*100) as "median_diff_percent" FROM
        (SELECT action_id, average, median FROM jltom.aggregate WHERE test_id = %s) a1,
        (SELECT action_id, average, median FROM jltom.aggregate WHERE test_id = %s) a2,
        jltom.action a
        WHERE a1.action_id = a2.action_id and a.id = a1.action_id
        """, [test_id_1, test_id_2])
    reasonable_percent = 3
    reasonable_abs_diff = 5 #ms
    negatives = []
    positives = []
    for row in data:
            if row.avg_diff_percent > reasonable_percent:
                negatives.append(row)
            elif row.avg_diff_percent < -reasonable_percent:
                positives.append(row)

    return render(request, 'compare_report.html',
                  {'negatives': negatives,
                   'positives': positives})

def dashboard(request):
    last_tests = []
    s = Test.objects.values('project_id').annotate(latest_time=Max('start_time'))
    for i in s:
        r = Test.objects.filter(project_id=i['project_id'],start_time=i['latest_time']).\
            values('project__project_name','display_name','id','project_id')
        last_tests.append(list(r)[0])
    return render(request, 'dashboard.html',
                  {'last_tests': last_tests})


class Analyze(TemplateView):
    def get(self, request, **kwargs):
        return render(request, 'analyze.html', context=None)


class History(TemplateView):
        def get(self, request, **kwargs):
            return render(request, 'history.html', context=None)

