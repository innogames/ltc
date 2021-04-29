from django.conf.urls import url, include
from django.contrib import admin
from django.conf.urls.static import static
from . import settings
from django.urls import path

admin.autodiscover()

urlpatterns = [
    path('admin', admin.site.urls),
    path('', include('ltc.web.urls'), name='index'),
    path('analyzer', include('ltc.analyzer.urls'), name='analyzer'),
    path('online', include('ltc.online.urls'), name='online'),
    path('controller', include('ltc.controller.urls'), name='controller'),
    path('administrator', include('ltc.administrator.urls'), name='administrator')
] + static(
    settings.STATIC_URL, document_root=settings.STATIC_URL
)
