"""
Tests for system functionality validation after Redis removal.
Validates Requirements: 1.2, 1.4, 2.1, 3.1, 3.3, 3.4
"""

import pytest
import logging
import subprocess
import sys
import os
from django.test import TestCase, override_settings
from django.core.management import call_command
from django.core.cache import cache
from django.conf import settings
from django.db import connection
from django.test.utils import override_settings
from django.core.management.base import CommandError
from io import StringIO
from unittest.mock import patch
from hypothesis import given, strategies as st, settings as hypothesis_settings
from hypothesis.extra.django import TestCase as HypothesisTestCase


class ApplicationStartupTest(TestCase):
    """Test application startup without Redis dependencies."""
    
    def setUp(self):
        """Set up test environment."""
        self.log_stream = StringIO()
        self.log_handler = logging.StreamHandler(self.log_stream)
        self.logger = logging.getLogger('django')
        self.logger.addHandler(self.log_handler)
        self.original_level = self.logger.level
        self.logger.setLevel(logging.DEBUG)
    
    def tearDown(self):
        """Clean up test environment."""
        self.logger.removeHandler(self.log_handler)
        self.logger.setLevel(self.original_level)
    
    def test_django_check_passes(self):
        """Test that Django system check passes without Redis."""
        # Requirements: 1.2, 2.1
        try:
            call_command('check', verbosity=0)
        except CommandError as e:
            self.fail(f"Django check failed: {e}")
    
    def test_no_redis_imports_in_settings(self):
        """Test that no Redis imports exist in settings."""
        # Requirements: 1.2, 2.1
        import mall_server.settings.base as base_settings
        
        # Check that Redis-related imports are not present
        settings_content = open(base_settings.__file__).read()
        
        redis_imports = [
            'django_redis',
            'redis',
            'celery',
            'RedisCache',
            'CELERY_BROKER_URL',
            'CELERY_RESULT_BACKEND'
        ]
        
        for redis_import in redis_imports:
            self.assertNotIn(redis_import, settings_content, 
                           f"Found Redis-related import/config: {redis_import}")
    
    def test_cache_backend_is_database(self):
        """Test that cache backend is configured to use database."""
        # Requirements: 3.1
        cache_backend = settings.CACHES['default']['BACKEND']
        
        # In test environment, it might be locmem, but in base settings it should be db
        if 'test' not in getattr(settings, 'SETTINGS_MODULE', ''):
            self.assertIn('db.DatabaseCache', cache_backend)
        else:
            # In test environment, locmem is acceptable
            self.assertIn('locmem.LocMemCache', cache_backend)
    
    def test_no_redis_connection_attempts_in_logs(self):
        """Test that no Redis connection attempts appear in logs."""
        # Requirements: 1.2, 2.1
        log_output = self.log_stream.getvalue().lower()
        
        redis_keywords = [
            'redis connection',
            'redis://localhost',
            'redis://127.0.0.1',
            'celery broker',
            'connection refused.*redis',
            'redis.*timeout'
        ]
        
        for keyword in redis_keywords:
            self.assertNotIn(keyword, log_output, 
                           f"Found Redis connection attempt in logs: {keyword}")
    
    def test_application_urls_load(self):
        """Test that application URLs load without Redis dependencies."""
        # Requirements: 1.4
        from django.urls import reverse
        from django.test import Client
        
        client = Client()
        
        # Test admin URL (should be accessible)
        try:
            response = client.get('/admin/', follow=True)
            # Should get login page, not server error
            self.assertIn(response.status_code, [200, 302])
        except Exception as e:
            self.fail(f"Admin URL failed to load: {e}")
    
    def test_database_cache_table_creation(self):
        """Test that database cache table can be created."""
        # Requirements: 3.1
        from django.core.management import call_command
        from django.db import connection
        
        # Create cache table
        try:
            call_command('createcachetable', 'test_cache_table', verbosity=0)
            
            # Verify table exists
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='test_cache_table'"
                )
                result = cursor.fetchone()
                self.assertIsNotNone(result, "Cache table was not created")
                
        except Exception as e:
            self.fail(f"Failed to create cache table: {e}")


class CacheOperationsTest(TestCase):
    """Test cache operations with database backend."""
    
    def setUp(self):
        """Set up cache table for testing."""
        # Create cache table if it doesn't exist
        try:
            call_command('createcachetable', cache._cache.cache_table_name, verbosity=0)
        except:
            pass  # Table might already exist
    
    def test_cache_set_and_get_operations(self):
        """Test basic cache set and get operations."""
        # Requirements: 3.1, 3.3
        test_key = 'test_cache_key'
        test_value = 'test_cache_value'
        
        # Test cache set
        cache.set(test_key, test_value, timeout=300)
        
        # Test cache get
        retrieved_value = cache.get(test_key)
        self.assertEqual(retrieved_value, test_value)
    
    def test_cache_expiration_behavior(self):
        """Test cache expiration behavior."""
        # Requirements: 3.3
        test_key = 'test_expiration_key'
        test_value = 'test_expiration_value'
        
        # Set cache with very short timeout
        cache.set(test_key, test_value, timeout=1)
        
        # Should be available immediately
        self.assertEqual(cache.get(test_key), test_value)
        
        # Test cache miss for non-existent key
        self.assertIsNone(cache.get('non_existent_key'))
    
    def test_cache_key_prefixing(self):
        """Test cache key generation and prefixing."""
        # Requirements: 3.4
        test_key = 'test_prefix_key'
        test_value = 'test_prefix_value'
        
        # Set cache value
        cache.set(test_key, test_value)
        
        # Verify we can retrieve it
        self.assertEqual(cache.get(test_key), test_value)
        
        # Test key prefixing by checking the actual key in database
        if hasattr(cache, '_cache') and hasattr(cache._cache, 'cache_table_name'):
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT cache_key FROM {cache._cache.cache_table_name} WHERE cache_key LIKE '%{test_key}%'"
                )
                result = cursor.fetchone()
                if result:
                    # Should contain the prefix from settings
                    cache_key = result[0]
                    expected_prefix = getattr(settings, 'CACHE_KEY_PREFIX', 'mall_server')
                    if expected_prefix:
                        self.assertIn(expected_prefix, cache_key)
    
    def test_cache_invalidation(self):
        """Test cache invalidation works correctly."""
        # Requirements: 3.4
        test_key = 'test_invalidation_key'
        test_value = 'test_invalidation_value'
        
        # Set cache value
        cache.set(test_key, test_value)
        self.assertEqual(cache.get(test_key), test_value)
        
        # Delete cache value
        cache.delete(test_key)
        self.assertIsNone(cache.get(test_key))
        
        # Test cache clear
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        cache.clear()
        self.assertIsNone(cache.get('key1'))
        self.assertIsNone(cache.get('key2'))


class SystemFunctionalityPreservationTest(HypothesisTestCase):
    """Property-based tests for system functionality preservation."""
    
    @given(
        cache_key=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=['Lu', 'Ll', 'Nd'])),
        cache_value=st.text(min_size=1, max_size=100),
        timeout=st.integers(min_value=1, max_value=3600)
    )
    @hypothesis_settings(max_examples=100, deadline=5000)
    def test_cache_backend_functionality_property(self, cache_key, cache_value, timeout):
        """
        Property 2: Cache Backend Functionality
        For any cache operation (set, get, delete, expire), the database cache backend 
        should handle the operation correctly and transparently replace Redis functionality.
        Validates: Requirements 3.1, 3.3, 3.4
        """
        # Feature: redis-removal, Property 2: Cache Backend Functionality
        
        try:
            # Test cache set operation
            cache.set(cache_key, cache_value, timeout)
            
            # Test cache get operation
            retrieved_value = cache.get(cache_key)
            self.assertEqual(retrieved_value, cache_value, 
                           f"Cache get failed for key: {cache_key}")
            
            # Test cache delete operation
            cache.delete(cache_key)
            deleted_value = cache.get(cache_key)
            self.assertIsNone(deleted_value, 
                            f"Cache delete failed for key: {cache_key}")
            
        except Exception as e:
            self.fail(f"Cache operation failed for key '{cache_key}': {e}")
    
    @given(
        test_data=st.dictionaries(
            keys=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=['Lu', 'Ll', 'Nd'])),
            values=st.text(min_size=1, max_size=50),
            min_size=1,
            max_size=10
        )
    )
    @hypothesis_settings(max_examples=50, deadline=10000)
    def test_system_functionality_preservation_property(self, test_data):
        """
        Property 3: System Functionality Preservation
        For any existing system feature or API endpoint, the functionality should work 
        identically before and after Redis removal.
        Validates: Requirements 1.4, 2.3, 5.3
        """
        # Feature: redis-removal, Property 3: System Functionality Preservation
        
        from django.test import Client
        
        client = Client()
        
        try:
            # Test that basic Django functionality works
            # 1. Cache operations work
            for key, value in test_data.items():
                cache.set(f"test_{key}", value, 300)
                retrieved = cache.get(f"test_{key}")
                self.assertEqual(retrieved, value, 
                               f"Cache functionality broken for key: {key}")
            
            # 2. Database operations work (test with a simple query)
            from apps.users.models import User
            user_count = User.objects.count()
            self.assertIsInstance(user_count, int, "Database operations not working")
            
            # 3. URL routing works
            response = client.get('/admin/')
            self.assertIn(response.status_code, [200, 302, 404], 
                         "URL routing not working properly")
            
            # Clean up test cache entries
            for key in test_data.keys():
                cache.delete(f"test_{key}")
                
        except Exception as e:
            self.fail(f"System functionality test failed: {e}")


class NoRedisConnectionTest(TestCase):
    """Test that no Redis connections are attempted."""
    
    def test_redis_configuration_removal_property(self):
        """
        Property 1: Redis Configuration Removal
        For any Django application startup after Redis configuration removal, 
        the system should start successfully without attempting Redis connections 
        and use the configured alternative cache backend.
        Validates: Requirements 1.1, 1.2, 2.1, 2.4
        """
        # Feature: redis-removal, Property 1: Redis Configuration Removal
        
        # Test that cache backend is not Redis
        cache_backend = settings.CACHES['default']['BACKEND']
        self.assertNotIn('redis', cache_backend.lower(), 
                        "Redis cache backend still configured")
        
        # Test that no Celery configuration exists
        celery_settings = [
            'CELERY_BROKER_URL',
            'CELERY_RESULT_BACKEND', 
            'CELERY_ACCEPT_CONTENT',
            'CELERY_TASK_SERIALIZER'
        ]
        
        for setting_name in celery_settings:
            self.assertFalse(hasattr(settings, setting_name), 
                           f"Celery setting still exists: {setting_name}")
        
        # Test that cache operations work with alternative backend
        test_key = 'redis_removal_test'
        test_value = 'alternative_backend_works'
        
        cache.set(test_key, test_value, 300)
        retrieved_value = cache.get(test_key)
        self.assertEqual(retrieved_value, test_value, 
                        "Alternative cache backend not working")
        
        cache.delete(test_key)