from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from ltc.api import views

router = DefaultRouter()
router.register('projects', views.ProjectViewSet, basename='project')
router.register('tests', views.TestViewSet, basename='test')
router.register(
    'loadgenerators', views.LoadGeneratorViewSet, basename='loadgenerator'
)

urlpatterns = [
    path('health_check', views.api_health_check, name='api_health_check'),
    path('users/me/', views.me, name='api.me'),
    path('schema/', SpectacularAPIView.as_view(), name='api.schema'),
    path(
        'schema/swagger/',
        SpectacularSwaggerView.as_view(url_name='api.schema'),
        name='api.swagger',
    ),
] + router.urls
