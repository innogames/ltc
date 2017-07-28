from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^projects_list', views.projects_list),
    url(r'^analyze$', views.Analyze.as_view()),
    url(r'^history$', views.History.as_view()),
    url(r'^dashboard', views.dashboard),
    url(r'^generate_overall_report', views.generate_overall_report),
    url(r'^project/(?P<project_id>\d+)/project_history/$',
        views.project_history),
    url(r'^project/(?P<project_id>\d+)/tests_list/$', views.tests_list),
    url(r'^project/(?P<project_id>\d+)/last_test/$', views.last_test),
    url(r'^project/(?P<project_id>\d+)/'
        r'(?P<build_number>\d+)/test_info/$', views.test_info),
    url(r'^project/(?P<test_id>\d+)/test_info/$', views.test_info_from_id),
    url(r'^project/(?P<project_id>\d+)/configure/$', views.configure_page),
    url(r'^test/(?P<test_id>\d+)/prev_test_id/$', views.prev_test_id),
    url(r'^test/(?P<test_id>\d+)/report/$', views.test_report),
    url(r'^test/(?P<test_id>\d+)/(?P<action_id>\d+)/action_report/$',
        views.action_report),
    url(r'^test/(?P<test_id>\d+)/action/(?P<action_id>\d+)/rtot/$',
        views.action_rtot),
    url(r'^test/(?P<test_id>\d+)/servers/$', views.test_servers),
    url(r'^test/(?P<test_id>\d+)/change/$', views.test_change),
    url(r'^test/(?P<test_id>\d+)/rtot/$', views.test_rtot),
    url(r'^test/(?P<test_id>\d+)/(?P<num_of_tests>\d+)/compare_avg/$',
        views.compare_tests_avg),
    url(r'^test/(?P<test_id>\d+)/(?P<num_of_tests>\d+)/compare_cpu/$',
        views.compare_tests_cpu),
    url(r'^test/(?P<test_id>\d+)/(?P<top_number>\d+)/top_avg/$',
        views.test_top_avg),
    url(r'^test/(?P<test_id>\d+)/top_errors/$', views.test_top_errors),
    url(r'^test/(?P<test_id>\d+)/errors/$', views.test_errors),
    url(r'^test/(?P<test_id>\d+)/(?P<server_id>\d+)/monitoring_metrics/$',
        views.available_test_monitoring_metrics),
    url(r'^test/(?P<test_id>\d+)/(?P<server_id>\d+)'
        r'/(?P<metric>[\w\-]+)/max_value/$', views.metric_max_value),
    url(r'^test/(?P<test_id>\d+)/(?P<server_id>\d+)'
        r'/(?P<metric>[\w\-]+)/get/$', views.metric_data),
    url(r'^test/(?P<test_id_1>\d+)/(?P<test_id_2>\d+)/compare_report/$',
        views.tests_compare_report),
    url(r'^test/(?P<test_id_1>\d+)/(?P<test_id_2>\d+)/compare_aggregate_data/$',
        views.tests_compare_aggregate),
]
