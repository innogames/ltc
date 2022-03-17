from django.conf.urls import url
from django.urls import path, re_path
from . import views

app_name = 'analyzer'

urlpatterns = [
    path('', views.index, name='analyzer.index'),
    url('test_data', views.test_data),
    url('compare_highlights', views.compare_highlights),
    path(
        '/action_details/<int:test_id>/<int:action_id>',
        views.action_details,
        name='action_details',
    ),
]
