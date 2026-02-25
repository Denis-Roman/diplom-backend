import os
from pathlib import Path

from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# Local overrides should win (e.g. SQLite for dev), while keeping `.env` usable for Azure.
load_dotenv(BASE_DIR / ".env.local", override=True)
load_dotenv(BASE_DIR / ".env", override=False)

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-change-me-in-production-!!!')
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-min-32-characters!')

DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')

def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in ('true', '1', 'yes')


def env_list(name: str, default: str = '') -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(',') if item.strip()]


ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', '*')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'rest_framework.authtoken',
    'school',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DB_ENGINE = os.getenv('DB_ENGINE', 'mssql').lower()

if DB_ENGINE in ('mssql', 'sqlserver', 'azure'):
    DB_AUTH = os.getenv('DB_AUTH', 'sql').lower()
    db_host = os.getenv('DB_HOST', '')
    db_user = os.getenv('DB_USER', '')

    # Azure SQL usually expects SQL user in the format: user@server
    # If a plain username is provided, append server short name automatically.
    if DB_AUTH not in ('aad', 'activedirectory', 'azuread', 'entra') and db_host.endswith('.database.windows.net'):
        if db_user and '@' not in db_user:
            server_short = db_host.split('.', 1)[0]
            db_user = f'{db_user}@{server_short}'

    extra_params = os.getenv(
        'DB_EXTRA_PARAMS',
        'Encrypt=yes;TrustServerCertificate=no;'
    )

    if DB_AUTH in ('aad', 'activedirectory', 'azuread', 'entra'):
        extra_params = f'Authentication=ActiveDirectoryPassword;{extra_params}'

    DATABASES = {
        'default': {
            'ENGINE': 'mssql',
            'NAME': os.getenv('DB_NAME', ''),
            'USER': db_user,
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': db_host,
            'PORT': os.getenv('DB_PORT', '1433'),
            'OPTIONS': {
                'driver': os.getenv('DB_DRIVER', 'ODBC Driver 18 for SQL Server'),
                'extra_params': extra_params,
            },
        }
    }
else:
    raise ImproperlyConfigured(
        "This project is configured to run only with MS SQL Server. "
        "Set DB_ENGINE to 'mssql' (or 'sqlserver'/'azure')."
    )

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'uk'
TIME_ZONE = 'Europe/Kyiv'
USE_I18N = True
USE_TZ = True

APPEND_SLASH = True



MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
CORS_ALLOW_ALL_ORIGINS = env_bool('CORS_ALLOW_ALL_ORIGINS', DEBUG)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS - allow Next.js frontend
CORS_ALLOWED_ORIGINS = env_list(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000'
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'school.authentication.JWTAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# Встановіть CSRF trusted origins
CSRF_TRUSTED_ORIGINS = env_list(
    'CSRF_TRUSTED_ORIGINS',
    'http://localhost:3000,http://127.0.0.1:3000'
)

SECURE_CROSS_ORIGIN_OPENER_POLICY = None

FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() in ('true', '1', 'yes')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'no-reply@localhost')
