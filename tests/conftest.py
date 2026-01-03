"""
Test configuration for Django mall server.
"""
import pytest
import os
import django
from django.conf import settings


def pytest_configure():
    """Configure Django settings for testing."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mall_server.settings.test')
    django.setup()


@pytest.fixture
def user_factory():
    """Factory for creating test users."""
    from apps.users.models import User
    
    def _create_user(**kwargs):
        defaults = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpassword123',
        }
        defaults.update(kwargs)
        return User.objects.create_user(**defaults)
    
    return _create_user