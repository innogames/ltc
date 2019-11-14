from django.urls import path
from . import views

urlpatterns = [
    path('/load_generators/get_data/', views.get_load_generators_data),
    path('/running_tests/', views.get_running_tests),
]
