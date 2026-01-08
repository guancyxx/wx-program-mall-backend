"""
Django settings for mall_server project.
All configurations are controlled via environment variables.
No hardcoded environment-specific logic - everything is configurable via .env file.
"""

import os
import pymysql
from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

# Configure PyMySQL to work with Django
pymysql.install_as_MySQLdb()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*', cast=Csv())

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
]

LOCAL_APPS = [
    'apps.users',
    'apps.membership',
    'apps.products',
    'apps.orders',
    'apps.payments',
    'apps.points',
    'apps.common',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mall_server.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'mall_server.wsgi.application'

# Database Configuration
# Use DB_ENGINE to select database backend: 'mysql' or 'sqlite3'
DB_ENGINE = config('DB_ENGINE', default='mysql')
if DB_ENGINE == 'sqlite3':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': config('DB_NAME', default=':memory:'),
            'OPTIONS': {
                'timeout': config('DB_TIMEOUT', default=20, cast=int),
            },
            'TEST': {
                'NAME': config('DB_TEST_NAME', default=':memory:'),
            }
        }
    }
else:
    # MySQL configuration
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('MYSQL_DATABASE', default='mall_server'),
            'USER': config('MYSQL_USER', default='root'),
            'PASSWORD': config('MYSQL_PASSWORD', default=''),
            'HOST': config('MYSQL_HOST', default='localhost'),
            'PORT': config('MYSQL_PORT', default='3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                'autocommit': True,
            },
            'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=60, cast=int),
            'CONN_HEALTH_CHECKS': config('DB_CONN_HEALTH_CHECKS', default=True, cast=bool),
        }
    }

# Password Hashers
# Use PASSWORD_HASHER_TYPE to select: 'secure' or 'md5' (for testing)
PASSWORD_HASHER_TYPE = config('PASSWORD_HASHER_TYPE', default='secure')
if PASSWORD_HASHER_TYPE == 'md5':
    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]
else:
    PASSWORD_HASHERS = [
        'apps.common.password_utils.SecurePasswordHasher',
        'apps.common.password_utils.BCryptPasswordHasher',
        'django.contrib.auth.hashers.PBKDF2PasswordHasher',
        'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
        'django.contrib.auth.hashers.Argon2PasswordHasher',
        'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    ]

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Authentication Backends
AUTHENTICATION_BACKENDS = [
    'apps.common.password_utils.SecureAuthenticationBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Password Security Configuration
PASSWORD_SECURITY_CONFIG = {
    'BCRYPT_ROUNDS': config('BCRYPT_ROUNDS', default=12, cast=int),
    'MIN_PASSWORD_LENGTH': 8,
    'MAX_PASSWORD_LENGTH': 128,
    'REQUIRE_UPPERCASE': True,
    'REQUIRE_LOWERCASE': True,
    'REQUIRE_NUMBERS': True,
    'REQUIRE_SPECIAL_CHARS': True,
    'ENABLE_LEGACY_MIGRATION': True,
    'LOG_SECURITY_EVENTS': True,
    'BRUTE_FORCE_THRESHOLD': 5,
    'BRUTE_FORCE_WINDOW_MINUTES': 15,
    'AUTO_MIGRATE_ON_LOGIN': True,
    'REQUIRE_PASSWORD_RESET_ON_CORRUPTION': True,
}

# Security Settings
SECURE_BROWSER_XSS_FILTER = config('SECURE_BROWSER_XSS_FILTER', default=True, cast=bool)
SECURE_CONTENT_TYPE_NOSNIFF = config('SECURE_CONTENT_TYPE_NOSNIFF', default=True, cast=bool)
X_FRAME_OPTIONS = config('X_FRAME_OPTIONS', default='DENY')
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=0, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=False, cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=False, cast=bool)

# Password Security Integration Settings
PASSWORD_RESET_TIMEOUT = 3600  # 1 hour for password reset tokens
PASSWORD_RESET_TIMEOUT_DAYS = 1  # Deprecated but kept for compatibility
LOGIN_ATTEMPTS_LIMIT = 5  # Maximum login attempts before lockout
LOGIN_ATTEMPTS_TIMEOUT = 900  # 15 minutes lockout duration
ACCOUNT_LOCKOUT_ENABLED = True
SECURITY_MONITORING_ENABLED = True

# Admin Security Settings
ADMIN_LOGIN_ATTEMPTS_LIMIT = 3  # Stricter limit for admin accounts
ADMIN_SESSION_TIMEOUT = 1800  # 30 minutes for admin sessions
ADMIN_REQUIRE_STRONG_PASSWORD = True

# CSRF Protection
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)
CSRF_COOKIE_HTTPONLY = config('CSRF_COOKIE_HTTPONLY', default=True, cast=bool)
CSRF_COOKIE_SAMESITE = config('CSRF_COOKIE_SAMESITE', default='Strict')
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='http://localhost:3000', cast=Csv())

# Session Security
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
SESSION_COOKIE_HTTPONLY = config('SESSION_COOKIE_HTTPONLY', default=True, cast=bool)
SESSION_COOKIE_SAMESITE = config('SESSION_COOKIE_SAMESITE', default='Strict')
SESSION_COOKIE_AGE = config('SESSION_COOKIE_AGE', default=3600, cast=int)  # 1 hour
SESSION_EXPIRE_AT_BROWSER_CLOSE = config('SESSION_EXPIRE_AT_BROWSER_CLOSE', default=True, cast=bool)
SESSION_ENGINE = config('SESSION_ENGINE', default='django.contrib.sessions.backends.db')

# Rate Limiting Configuration
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

# Internationalization
LANGUAGE_CODE = config('LANGUAGE_CODE', default='zh-hans')
TIME_ZONE = config('TIME_ZONE', default='Asia/Shanghai')
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': config('DRF_PAGE_SIZE', default=20, cast=int),
    'EXCEPTION_HANDLER': 'apps.common.exceptions.custom_exception_handler',
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=config('JWT_ACCESS_TOKEN_LIFETIME_DAYS', default=7, cast=int)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=config('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=30, cast=int)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

# CORS Settings
CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL_ORIGINS', default=True, cast=bool)
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:3000,http://127.0.0.1:3000', cast=Csv())

# Cache Configuration
# Use CACHE_BACKEND to select: 'db', 'locmem', or 'dummy'
CACHE_BACKEND = config('CACHE_BACKEND', default='db')
if CACHE_BACKEND == 'locmem':
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
elif CACHE_BACKEND == 'dummy':
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }
else:
    # DatabaseCache
    cache_max_entries = config('CACHE_MAX_ENTRIES', default=10000, cast=int)
    cache_cull_frequency = config('CACHE_CULL_FREQUENCY', default=3, cast=int)
    cache_timeout = config('CACHE_TIMEOUT', default=300, cast=int)
    
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': config('CACHE_LOCATION', default='mall_server_cache'),
            'TIMEOUT': cache_timeout,
            'OPTIONS': {
                'MAX_ENTRIES': cache_max_entries,
                'CULL_FREQUENCY': cache_cull_frequency,
            },
            'KEY_PREFIX': config('CACHE_KEY_PREFIX', default='mall_server'),
        }
    }
    
    # Optional: Add separate cache backends if enabled
    if config('CACHE_ENABLE_SESSIONS', default=False, cast=bool):
        CACHES['sessions'] = {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': config('CACHE_SESSIONS_LOCATION', default='mall_server_sessions_cache'),
            'TIMEOUT': config('CACHE_SESSIONS_TIMEOUT', default=1800, cast=int),
            'OPTIONS': {
                'MAX_ENTRIES': config('CACHE_SESSIONS_MAX_ENTRIES', default=5000, cast=int),
                'CULL_FREQUENCY': config('CACHE_SESSIONS_CULL_FREQUENCY', default=3, cast=int),
            },
            'KEY_PREFIX': config('CACHE_SESSIONS_KEY_PREFIX', default='mall_sessions'),
        }
    
    if config('CACHE_ENABLE_STATIC', default=False, cast=bool):
        CACHES['static_data'] = {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': config('CACHE_STATIC_LOCATION', default='mall_server_static_cache'),
            'TIMEOUT': config('CACHE_STATIC_TIMEOUT', default=7200, cast=int),
            'OPTIONS': {
                'MAX_ENTRIES': config('CACHE_STATIC_MAX_ENTRIES', default=3000, cast=int),
                'CULL_FREQUENCY': config('CACHE_STATIC_CULL_FREQUENCY', default=5, cast=int),
            },
            'KEY_PREFIX': config('CACHE_STATIC_KEY_PREFIX', default='mall_static'),
        }

# Email Configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# Logging Configuration
# Set LOGGING_DISABLE to True to disable logging configuration
if config('LOGGING_DISABLE', default=False, cast=bool):
    LOGGING_CONFIG = None
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'null': {
                'class': 'logging.NullHandler',
            },
        },
        'root': {
            'handlers': ['null'],
        },
    }

# WeChat Configuration
WECHAT_APPID = config('WECHAT_APPID', default='')
WECHAT_APPSECRET = config('WECHAT_APPSECRET', default='')
WECHAT_MCHID = config('WECHAT_MCHID', default='')
WECHAT_MCH_ID = config('WECHAT_MCH_ID', default=WECHAT_MCHID)  # Alias for consistency
WECHAT_API_KEY = config('WECHAT_API_KEY', default='')
WECHAT_NOTIFY_URL = config('WECHAT_NOTIFY_URL', default='http://localhost:8000/api/order/callback')
WECHAT_CERT_PATH = config('WECHAT_CERT_PATH', default='')
WECHAT_KEY_PATH = config('WECHAT_KEY_PATH', default='')

# Test-specific settings
TEST_RUNNER = config('TEST_RUNNER', default='django.test.runner.DiscoverRunner')
TEST_MEDIA_ROOT = config('TEST_MEDIA_ROOT', default=None)
TEST_STATIC_ROOT = config('TEST_STATIC_ROOT', default=None)

if TEST_MEDIA_ROOT:
    MEDIA_ROOT = TEST_MEDIA_ROOT
if TEST_STATIC_ROOT:
    STATIC_ROOT = TEST_STATIC_ROOT

