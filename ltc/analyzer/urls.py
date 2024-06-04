from django.urls import path, re_path
from . import views

app_name = 'analyzer'

urlpatterns = [
    path('', views.index, name='analyzer.index'),
    path('test_data', views.test_data),
    path('compare_highlights', views.compare_highlights),
    path(
        '/action_details/<int:test_id>/<int:action_id>',
        views.action_details,
        name='action_details',
    ),
]
