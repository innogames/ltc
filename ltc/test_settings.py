"""
Test settings: SQLite so the suite runs without a PostgreSQL server.
JSONB key access goes through KeyTextTransform/Cast (see
ltc/base/models.py json_num), which works on both backends.
Run against real PostgreSQL with: pytest --ds=ltc.settings
"""
from ltc.settings import *  # NOQA

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
