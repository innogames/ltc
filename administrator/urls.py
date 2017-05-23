from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.administrator_page),
    url(r'^new_jd/$', views.new_jd_page),
    url(r'^jd/(?P<jd_id>\d+)/delete/', views.delete_jd),
    url(r'^jd/(?P<jd_id>\d+)/create/$', views.create_jd),
    url(r'^new_ssh_key/$', views.new_ssh_key_page),
    url(r'^ssh_key/(?P<ssh_key_id>\d+)/delete/', views.delete_ssh_key),
    url(r'^ssh_key/(?P<ssh_key_id>\d+)/create/$', views.create_ssh_key),
]
