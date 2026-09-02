# Optional local override file — copy to ltc/local_settings.py for development.
# Production should configure everything via environment variables instead:
#
#   LTC_SECRET_KEY            Django secret key (required in production)
#   LTC_DEBUG                 'true' / 'false' (default: true — dev only!)
#   LTC_ALLOWED_HOSTS         comma-separated hostnames
#   LTC_DB_NAME / LTC_DB_USER / LTC_DB_PASSWORD / LTC_DB_HOST / LTC_DB_PORT
#   LTC_LOGIN_URL             SSO login URL (default: /loginapi/login/)
#   LTC_GRAPHITE_URL / LTC_GRAPHITE_USER / LTC_GRAPHITE_PASSWORD
#   LTC_WIKI_URL / LTC_WIKI_USER / LTC_WIKI_PASS      (Confluence publishing)
#   LTC_CORS_ALLOWED_ORIGINS  comma-separated (default: http://localhost:5173)

DEBUG = True

ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ltc2',
        'USER': 'postgres',
        'PASSWORD': '123456',
        'HOST': 'localhost',
        'PORT': 5432,
    }
}
