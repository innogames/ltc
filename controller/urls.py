from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^proxy/(?P<proxy_id>\d+)/set_delay/$',
        views.change_proxy_delay),
    url(r'^proxy/(?P<proxy_id>\d+)/start/$',
        views.start_proxy, name='start_proxy'),
    url(r'^proxy/(?P<proxy_id>\d+)/stop/$',
        views.stop_proxy, name='stop_proxy'),
    url(r'^proxy/new_proxy/$',
        views.new_proxy_page, name='new_proxy_page'),
    url(r'^proxy/new_proxy/add/$',
        views.add_proxy, name='new_proxy_page'),
    url(r'^$',
        views.controller_page),
    url(r'^project/(?P<project_id>\d+)/configure_test$',
        views.configure_test),
    url(r'^project/(?P<project_id>\d+)/start_test',
        views.start_test),
    url(r'^running_test/(?P<running_test_id>\d+)/stop_test',
        views.stop_test),
]

