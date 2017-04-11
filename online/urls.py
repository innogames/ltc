from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^tests_list', views.tests_list),
    url(r'^(?P<running_test_id>\d+)/update/', views.update),
    url(r'^(?P<running_test_id>\d+)/rtot/', views.online_test_rtot),
    url(r'^(?P<running_test_id>\d+)/success_rate/', views.online_test_success_rate),
    url(r'^(?P<running_test_id>\d+)/rps/', views.online_test_rps),
    url(r'^(?P<running_test_id>\d+)/response_codes/', views.online_test_response_codes),
    url(r'^(?P<running_test_id>\d+)/aggregate/', views.online_test_aggregate),

    url(r'^(?P<test_id>\d+)/online_page/', views.OnlinePage.as_view())
]
