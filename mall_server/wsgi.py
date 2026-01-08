"""
WSGI config for mall_server project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mall_server.settings')

application = get_wsgi_application()