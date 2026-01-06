"""
Django settings for mall_server project.
Base settings shared across all environments.
"""

import os
import pymysql
from pathlib import Path
from decouple import config

# Configure PyMySQL to work with Django
pymysql.install_as_MySQLdb()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*', cast=lambda v: [s.strip() for s in v.split(',')])

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
    'apps.common.middleware.SecurityMiddleware',
    'apps.common.middleware.ErrorHandlingMiddleware',
    'apps.common.performance.PerformanceMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.common.middleware.NodeJSCompatibilityMiddleware',
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

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('MYSQL_DATABASE', default='mall_server'),
        'USER': config('MYSQL_USERNAME', default='root'),
        'PASSWORD': config('MYSQL_PASSWORD', default=''),
        'HOST': config('MYSQL_HOST', default='localhost'),
        'PORT': config('MYSQL_PORT', default='3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'autocommit': True,
            # Connection pooling and performance options
            'pool_size': 20,
            'max_overflow': 30,
            'pool_timeout': 30,
            'pool_recycle': 3600,
        },
        'CONN_MAX_AGE': 600,  # Keep connections alive for 10 minutes
    }
}

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

# Password Hashers (secure bcrypt first for enhanced security)
PASSWORD_HASHERS = [
    'apps.common.password_utils.SecurePasswordHasher',
    'apps.common.password_utils.BCryptPasswordHasher',  # Fallback for existing hashes
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# Authentication Backends (secure backend first)
AUTHENTICATION_BACKENDS = [
    'apps.common.password_utils.SecureAuthenticationBackend',
    'django.contrib.auth.backends.ModelBackend',  # Fallback for compatibility
]

# Password Security Configuration
PASSWORD_SECURITY_CONFIG = {
    'BCRYPT_ROUNDS': 12,
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
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000 if not config('DEBUG', default=True, cast=bool) else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

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
CSRF_COOKIE_SECURE = not config('DEBUG', default=True, cast=bool)
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='http://localhost:3000', cast=lambda v: [s.strip() for s in v.split(',')])

# Session Security
SESSION_COOKIE_SECURE = not config('DEBUG', default=True, cast=bool)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Rate Limiting Configuration
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

# Internationalization
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
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
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'apps.common.exceptions.custom_exception_handler',
}

# JWT Settings
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

# CORS Settings
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
        'security': {
            'format': '[SECURITY] %(asctime)s %(levelname)s %(message)s',
            'style': '%',
        },
        'audit': {
            'format': '[AUDIT] %(asctime)s %(levelname)s %(message)s',
            'style': '%',
        },
        'json': {
            'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "module": "%(module)s", "process": %(process)d, "thread": %(thread)d}',
            'style': '%',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'security_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'formatter': 'security',
        },
        'audit_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'audit.log',
            'formatter': 'audit',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'errors.log',
            'formatter': 'verbose',
        },
        'security_alerts': {
            'level': 'CRITICAL',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'security_alerts.log',
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'security': {
            'handlers': ['security_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'security.controller': {
            'handlers': ['security_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'security.auth_backend': {
            'handlers': ['security_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'security.migration': {
            'handlers': ['security_file', 'audit_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'security.audit': {
            'handlers': ['audit_file', 'security_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'security.alerts': {
            'handlers': ['security_alerts', 'security_file', 'console'],
            'level': 'CRITICAL',
            'propagate': False,
        },
        'performance': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security_file', 'error_file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# WeChat Configuration
WECHAT_APPID = config('WECHAT_APPID', default='')
WECHAT_APPSECRET = config('WECHAT_APPSECRET', default='')
WECHAT_MCHID = config('WECHAT_MCHID', default='')
WECHAT_MCH_ID = config('WECHAT_MCH_ID', default=WECHAT_MCHID)  # Alias for consistency
WECHAT_API_KEY = config('WECHAT_API_KEY', default='')
WECHAT_NOTIFY_URL = config('WECHAT_NOTIFY_URL', default='http://localhost:8000/api/order/callback')
WECHAT_CERT_PATH = config('WECHAT_CERT_PATH', default='')  # Path to WeChat Pay certificate
WECHAT_KEY_PATH = config('WECHAT_KEY_PATH', default='')   # Path to WeChat Pay private key

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'mall_server_cache',
        'TIMEOUT': 300,  # Default timeout: 5 minutes
        'OPTIONS': {
            'MAX_ENTRIES': 10000,
            'CULL_FREQUENCY': 3,
        },
        'KEY_PREFIX': 'mall_server',
    }
}

