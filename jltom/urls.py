"""jltom URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from django.conf.urls.static import static
from . import settings

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^', include('jltom_web.urls')),
    url(r'^analyzer/', include('analyzer.urls')),
    url(r'^online/', include('online.urls')),
    url(r'^controller/', include('controller.urls', namespace="controller")),
    url(r'^administrator/',
        include('administrator.urls', namespace="administrator")),
] + static(
    settings.STATIC_URL, document_root=settings.STATIC_URL)
