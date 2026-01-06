#!/usr/bin/env python
"""
Direct test of health endpoint view functionality.
"""
import os
import sys
import django
import json
from django.conf import settings
from django.test import RequestFactory
from django.http import HttpRequest

# Set up Django with minimal settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mall_server.settings.test_sqlite')
django.setup()

from apps.common.health_views import BasicHealthCheckView

def test_health_view_directly():
    """Test the health view directly without URL routing."""
    print("Testing Health View Directly...")
    print("=" * 50)
    
    try:
        # Create a request factory
        factory = RequestFactory()
        
        # Create a GET request to /health/
        request = factory.get('/health/')
        
        # Create the view instance
        view = BasicHealthCheckView()
        
        # Call the view dir