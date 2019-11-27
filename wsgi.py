import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jltc.settings')

# This application object is used by the development server
# as well as any WSGI server configured to use this file.
application = get_wsgi_application()
