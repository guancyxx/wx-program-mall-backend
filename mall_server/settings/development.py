"""
Development settings for mall_server project.
"""

import os
from decouple import config
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

# Database - MySQL/MariaDB for development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('MYSQL_DATABASE', default='mall_server_dev'),
        'USER': config('MYSQL_USER', default='root'),
        'PASSWORD': config('MYSQL_PASSWORD', default='dev_password'),
        'HOST': config('MYSQL_HOST', default='localhost'),
        'PORT': config('MYSQL_PORT', default='3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'sql_mode': 'STRICT_TRANS_TABLES',
        },
        'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=60, cast=int),  # Connection pooling
        'CONN_HEALTH_CHECKS': True,  # Health checks for connections
    }
}

# Redis Configuration for development
REDIS_HOST = config('REDIS_HOST', default='localhost')
REDIS_PORT = config('REDIS_PORT', default=6379, cast=int)
REDIS_PASSWORD = config('REDIS_PASSWORD', default='redis_password')

# Cache configuration using Redis
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Session configuration using Redis
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Email backend for development
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')

# Additional development apps
# INSTALLED_APPS += [
#     'django_extensions',
# ]

# Development middleware
MIDDLEWARE += [
    'django.middleware.common.BrokenLinkEmailsMiddleware',
]

# Logging for development
LOGGING['handlers']['console']['level'] = config('LOG_LEVEL', default='DEBUG')
LOGGING['root']['level'] = config('LOG_LEVEL', default='DEBUG')

# WeChat Configuration
WECHAT_APPID = config('WECHAT_APPID', default='')
WECHAT_APPSECRET = config('WECHAT_APPSECRET', default='')

# JWT Configuration
JWT_SECRET_KEY = config('JWT_SECRET_KEY', default='tokenTp')
JWT_ALGORITHM = config('JWT_ALGORITHM', default='HS256')
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = config('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', default=1440, cast=int)