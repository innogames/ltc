from django.conf import settings
from django.contrib import admin
from django.contrib.auth.views import logout_then_login
from django.urls import include, path, re_path

from ltc.base.views import spa

admin.autodiscover()

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path(r'api/(?P<version>(v1))/', include('ltc.api.urls')),
    path('logout/', logout_then_login, name='logout'),
]

# InnoGames SSO endpoints, only when the internal package is installed
# (mirrors the conditional app registration in ltc/settings.py).
if getattr(settings, 'HAS_IGRESTLOGIN', False):
    urlpatterns.append(
        re_path(r'^loginapi/?', include('igrestlogin.urls'))
    )

# React SPA catch-all — everything that is not API/admin/auth/static.
# Client-side routes (/, /analyzer, /online) must survive a page reload.
urlpatterns.append(
    re_path(
        r'^(?!api/|admin/|loginapi|logout/|static/).*$',
        spa,
        name='spa',
    )
)
