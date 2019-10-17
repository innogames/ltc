from django.conf.urls import url
from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='analyzer.index'),
    url('test_data', views.test_data),
    url('compare_highlights', views.compare_highlights),
    path(
        '/action_details/(?P<test_id>\d+)/(?P<action_id>\d+)',
        views.action_details,
        name='action_details',
    ),
]
