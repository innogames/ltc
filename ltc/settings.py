import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Core security/env settings. Real values come from environment variables
# (see ltc/local_settings.example.py); defaults are only safe for local dev.
SECRET_KEY = os.environ.get('LTC_SECRET_KEY', 'insecure-dev-only-key')
DEBUG = os.environ.get('LTC_DEBUG', 'true').lower() in ('1', 'true', 'yes')
ALLOWED_HOSTS = [
    h for h in os.environ.get('LTC_ALLOWED_HOSTS', '').split(',') if h
]

# Application definition

INSTALLED_APPS = [
    'ltc.admin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'corsheaders',
    'ltc.base',
    'ltc.analyzer',
    'ltc.online',
    'ltc.controller',
    'ltc.api',
]

# igrestlogin (InnoGames SSO) is an internal package that may be absent in
# open-source/dev checkouts; enable it only when installed. find_spec avoids
# importing the package (its models can't load before the app registry).
from importlib.util import find_spec  # NOQA: E402

HAS_IGRESTLOGIN = find_spec('igrestlogin') is not None
if HAS_IGRESTLOGIN:
    INSTALLED_APPS.append('igrestlogin')
    AUTHENTICATION_BACKENDS = [
        'igrestlogin.backends.RestLoginBackend',
        'django.contrib.auth.backends.ModelBackend',
    ]
    # igrestlogin's !redirect view bounces to the SSO portal
    # (IGRESTLOGIN_AUTHURL) and back via ?next=.
    LOGIN_URL = os.environ.get('LTC_LOGIN_URL', '/loginapi/!redirect')
    IGRESTLOGIN_AUTHURL = os.environ.get('LTC_IGRESTLOGIN_AUTHURL', '')
else:
    AUTHENTICATION_BACKENDS = [
        'django.contrib.auth.backends.ModelBackend',
    ]
    LOGIN_URL = os.environ.get('LTC_LOGIN_URL', '/admin/login/')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ltc.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # frontend/dist lets the SPA catch-all serve the built index.html
        'DIRS': [os.path.join(BASE_DIR, 'frontend', 'dist')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'builtins': [
                'ltc.templatetags.tags',
            ]
        },
    },
]

WSGI_APPLICATION = 'ltc.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('LTC_DB_NAME', 'ltc2'),
        'USER': os.environ.get('LTC_DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('LTC_DB_PASSWORD', ''),
        'HOST': os.environ.get('LTC_DB_HOST', 'localhost'),
        'PORT': int(os.environ.get('LTC_DB_PORT', '5432')),
    }
}

# Existing tables were created with AutoField primary keys; keep it that way
# to avoid a fleet of BigAutoField migrations.
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# External integrations (Graphite metrics, Confluence publishing)
GRAPHITE_URL = os.environ.get('LTC_GRAPHITE_URL', '')
GRAPHITE_USER = os.environ.get('LTC_GRAPHITE_USER', '')
GRAPHITE_PASSWORD = os.environ.get('LTC_GRAPHITE_PASSWORD', '')
WIKI_URL = os.environ.get('LTC_WIKI_URL', '')
WIKI_USER = os.environ.get('LTC_WIKI_USER', '')
WIKI_PASS = os.environ.get('LTC_WIKI_PASS', '')

# REST API
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_VERSIONING_CLASS':
        'rest_framework.versioning.URLPathVersioning',
    'ALLOWED_VERSIONS': ['v1'],
    'DEFAULT_VERSION': 'v1',
    'DEFAULT_PAGINATION_CLASS':
        'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'LTC API',
    'DESCRIPTION': 'Load Testing Center REST API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': r'/api/v(?P<version>[0-9]+)',
}

# CORS: only needed for the Vite dev server; production is same-origin.
CORS_ALLOWED_ORIGINS = [
    o for o in os.environ.get(
        'LTC_CORS_ALLOWED_ORIGINS', 'http://localhost:5173'
    ).split(',') if o
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME':
        'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME':
        'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME':
        'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME':
        'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/
STATIC_ROOT = os.path.join(BASE_DIR, '_static')
STATIC_URL = '/static/'
# The built React SPA — run `make frontend-build` first (see
# .claude/docs/frontend.md). Guarded so manage.py works without a build.
STATICFILES_DIRS = []
_frontend_dist = os.path.join(BASE_DIR, 'frontend', 'dist')
if os.path.isdir(_frontend_dist):
    STATICFILES_DIRS.append(_frontend_dist)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'main_formatter': {
            'format': '\033[94m[%(levelname)s]: (%(asctime)s)\033[0m '
            '%(message)s ',
            'datefmt': "%Y-%m-%d %H:%M:%S",
        },
        'debug_formatter': {
            'format': '[%(levelname)s]: (%(asctime)s; %(filename)s:%(lineno)d) '
                       '%(message)s ',
            'datefmt': "%Y-%m-%d %H:%M:%S",
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'main_formatter',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': "INFO",
        },
    }
}

# Optional local override for development; production must use env vars.
try:
    from .local_settings import *  # NOQA
except ImportError:
    pass
