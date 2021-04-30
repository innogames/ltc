from django.urls import path

import ltc.api.views as views

urlpatterns = [
    path('', views.api_root, name='api_root'),
    path('health_check', views.api_health_check, name='api_health_check'),
]
