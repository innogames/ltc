# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'SECRET_KEY'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

X_FRAME_OPTIONS = 'ALLOW'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'ltc2',
        'USER': 'postgres',
        'PASSWORD': '123456',
        'HOST': 'localhost',
    }
}
