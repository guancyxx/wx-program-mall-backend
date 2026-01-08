"""
ASGI config for mall_server project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mall_server.settings')

application = get_asgi_application()