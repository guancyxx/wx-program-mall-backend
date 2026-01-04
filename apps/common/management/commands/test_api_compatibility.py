"""
API compatibility testing script

This script tests the Django API endpoints against the expected Node.js behavior
to ensure frontend compatibility during migration.

Usage:
    python manage.py test_api_compatibility --base-url http://localhost:8000
    python manage.py test_api_compatibility --base-url http://localhost:8000 --verbose
"""

import json
import requests
import logging
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

# Setup logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test API compatibility with Node.js frontend expectations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--base-url',
            type=str,
            default='http://localhost:8000',
            help='Base URL for API testing (default: http://localhost:8000)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed test output'
        )
        parser.add_argument(
            '--test-user-email',
            type=str,
            default='test@example.com',
            help='Test user email for authentication tests'
        )
        parser.add_argument(
            '--test-user-phone',
            type=str,
            default='13800138000',
            help='Test user phone for authentication tests'
        )

    def handle(self, *args, **options):
        self.base_url = options['base_url'].rstrip('/')
        self.verbose = options['verbose']
        self.test_user_email = options['test_user_email']
        self.test_user_phone = options['test_user_phone']

        # Initialize test results
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'errors': []
        }

        self.stdout.write(self.style.SUCCESS(f'Starting API compatibility tests against {self.base_url}'))

        try:
            # Setup test data
            self.setup_test_data()

            # Run compatibility tests
            self.test_response_format_compatibility()
            self.test_authentication_compatibility()
            self.test_user_endpoints_compatibility()
            self.test_product_endpoints_compatibility()
            self.test_order_endpoints_compatibility()
            self.test_error_handling_compatibility()

            # Print test results
            self.print_test_results()

        except Exception as e:
            logger.error(f'Test suite failed: {e}')
            raise CommandError(f'Test suite failed: {e}')

    def setup_test_data(self):
        """Setup test data for compatibility testing"""
        self.stdout.write('Setting up test data...')
        
        # Create or get test user
        self.test_user, created = User.objects.get_or_create(
            username='test_user',
            defaults={
                'email': self.test_user_email,
                'phone': self.test_user_phone,
                'wechat_openid': 'test_openid_123',
                'is_active': True
            }
        )
        
        if created:
            self.test_user.set_password('testpass123')
            self.test_user.save()

        # Generate JWT token for authenticated requests
        refresh = RefreshToken.for_user(self.test_user)
        self.auth_token = str(refresh.access_token)

        self.stdout.write(f'Test user created/found: {self.test_user.username}')

    def make_request(self, method, endpoint, data=None, headers=None, auth=True):
        """Make HTTP request with proper headers and authentication"""
        url = f"{self.base_url}{endpoint}"
        
        default_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if headers:
            default_headers.update(headers)
        
        if auth and hasattr(self, 'auth_token'):
            default_headers['Authorization'] = f'Bearer {self.auth_token}'

        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=default_headers, params=data)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=default_headers, json=data)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=default_headers, json=data)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=default_headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            return response
        except requests.exceptions.RequestException as e:
            self.add_error(f"Request failed for {method} {endpoint}: {e}")
            return None

    def test_response_format_compatibility(self):
        """Test that all responses follow Node.js format"""
        self.stdout.write('Testing response format compatibility...')
        
        # Test success response format
        response = self.make_request('GET', '/api/products/', auth=False)
        if response and response.status_code == 200:
            try:
                data = response.json()
                if self.validate_nodejs_response_format(data, success=True):
                    self.add_success('Response format - Success response')
                else:
                    self.add_error('Response format - Success response does not match Node.js format')
            except json.JSONDecodeError:
                self.add_error('Response format - Invalid JSON in success response')
        else:
            self.add_error('Response format - Failed to get success response')

        # Test error response format
        response = self.make_request('GET', '/api/nonexistent-endpoint/', auth=False)
        if response and response.status_code >= 400:
            try:
                data = response.json()
                if self.validate_nodejs_response_format(data, success=False):
                    self.add_success('Response format - Error response')
                else:
                    self.add_error('Response format - Error response does not match Node.js format')
            except json.JSONDecodeError:
                self.add_error('Response format - Invalid JSON in error response')

    def test_authentication_compatibility(self):
        """Test authentication endpoint compatibility"""
        self.stdout.write('Testing authentication compatibility...')
        
        # Test password login
        login_data = {
            'phone': self.test_user_phone,
            'password': 'testpass123'
        }
        
        response = self.make_request('POST', '/api/users/password-login/', login_data, auth=False)
        if response and response.status_code == 200:
            try:
                data = response.json()
                if (self.validate_nodejs_response_format(data, success=True) and
                    'token' in data.get('data', {}) and
                    'uid' in data.get('data', {})):
                    self.add_success('Authentication - Password login format')
                    # Update auth token for subsequent tests
                    self.auth_token = data['data']['token']
                else:
                    self.add_error('Authentication - Password login response format incorrect')
            except json.JSONDecodeError:
                self.add_error('Authentication - Invalid JSON in login response')
        else:
            self.add_error(f'Authentication - Password login failed with status {response.status_code if response else "No response"}')

    def test_user_endpoints_compatibility(self):
        """Test user management endpoint compatibility"""
        self.stdout.write('Testing user endpoints compatibility...')
        
        # Test get user info
        response = self.make_request('GET', '/api/users/profile/')
        if response and response.status_code == 200:
            try:
                data = response.json()
                if (self.validate_nodejs_response_format(data, success=True) and
                    isinstance(data.get('data'), dict)):
                    self.add_success('User endpoints - Get user info')
                else:
                    self.add_error('User endpoints - Get user info format incorrect')
            except json.JSONDecodeError:
                self.add_error('User endpoints - Invalid JSON in user info response')
        else:
            self.add_error('User endpoints - Get user info failed')

        # Test update user info
        update_data = {
            'username': 'Updated Test User'
        }
        response = self.make_request('PUT', '/api/users/profile/', update_data)
        if response and response.status_code == 200:
            try:
                data = response.json()
                if self.validate_nodejs_response_format(data, success=True):
                    self.add_success('User endpoints - Update user info')
                else:
                    self.add_error('User endpoints - Update user info format incorrect')
            except json.JSONDecodeError:
                self.add_error('User endpoints - Invalid JSON in update response')

    def test_product_endpoints_compatibility(self):
        """Test product endpoint compatibility"""
        self.stdout.write('Testing product endpoints compatibility...')
        
        # Test get products list
        response = self.make_request('GET', '/api/products/', auth=False)
        if response and response.status_code == 200:
            try:
                data = response.json()
                if (self.validate_nodejs_response_format(data, success=True) and
                    'list' in data.get('data', {}) and
                    'page' in data.get('data', {})):
                    self.add_success('Product endpoints - Get products list')
                else:
                    self.add_error('Product endpoints - Get products list format incorrect')
            except json.JSONDecodeError:
                self.add_error('Product endpoints - Invalid JSON in products response')
        else:
            self.add_error('Product endpoints - Get products list failed')

        # Test product search with parameters
        search_params = {
            'keyword': 'test',
            'page': 1,
            'pageSize': 10
        }
        response = self.make_request('GET', '/api/products/', search_params, auth=False)
        if response and response.status_code == 200:
            try:
                data = response.json()
                if self.validate_nodejs_response_format(data, success=True):
                    self.add_success('Product endpoints - Product search with parameters')
                else:
                    self.add_error('Product endpoints - Product search format incorrect')
            except json.JSONDecodeError:
                self.add_error('Product endpoints - Invalid JSON in search response')

    def test_order_endpoints_compatibility(self):
        """Test order endpoint compatibility"""
        self.stdout.write('Testing order endpoints compatibility...')
        
        # Test get user orders
        response = self.make_request('GET', '/api/orders/')
        if response and response.status_code == 200:
            try:
                data = response.json()
                if (self.validate_nodejs_response_format(data, success=True) and
                    isinstance(data.get('data'), list)):
                    self.add_success('Order endpoints - Get user orders')
                else:
                    self.add_error('Order endpoints - Get user orders format incorrect')
            except json.JSONDecodeError:
                self.add_error('Order endpoints - Invalid JSON in orders response')
        else:
            self.add_error('Order endpoints - Get user orders failed')

    def test_error_handling_compatibility(self):
        """Test error handling compatibility"""
        self.stdout.write('Testing error handling compatibility...')
        
        # Test 404 error
        response = self.make_request('GET', '/api/nonexistent/', auth=False)
        if response and response.status_code == 404:
            try:
                data = response.json()
                if (self.validate_nodejs_response_format(data, success=False) and
                    data.get('code') != 200):
                    self.add_success('Error handling - 404 error format')
                else:
                    self.add_error('Error handling - 404 error format incorrect')
            except json.JSONDecodeError:
                self.add_error('Error handling - Invalid JSON in 404 response')

        # Test authentication error
        response = self.make_request('GET', '/api/users/profile/', auth=False)
        if response and response.status_code == 401:
            try:
                data = response.json()
                if (self.validate_nodejs_response_format(data, success=False) and
                    data.get('code') != 200):
                    self.add_success('Error handling - Authentication error format')
                else:
                    self.add_error('Error handling - Authentication error format incorrect')
            except json.JSONDecodeError:
                self.add_error('Error handling - Invalid JSON in auth error response')

    def validate_nodejs_response_format(self, data, success=True):
        """Validate that response follows Node.js format"""
        if not isinstance(data, dict):
            return False
        
        # Check required fields
        if 'code' not in data or 'msg' not in data or 'data' not in data:
            return False
        
        # Check success response
        if success:
            return data['code'] == 200
        else:
            return data['code'] != 200 and data['data'] is None
        
        return True

    def add_success(self, test_name):
        """Record a successful test"""
        self.test_results['passed'] += 1
        if self.verbose:
            self.stdout.write(self.style.SUCCESS(f'✓ {test_name}'))

    def add_error(self, error_message):
        """Record a failed test"""
        self.test_results['failed'] += 1
        self.test_results['errors'].append(error_message)
        if self.verbose:
            self.stdout.write(self.style.ERROR(f'✗ {error_message}'))

    def print_test_results(self):
        """Print final test results"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('API COMPATIBILITY TEST RESULTS'))
        self.stdout.write('='*60)
        
        total_tests = self.test_results['passed'] + self.test_results['failed']
        passed = self.test_results['passed']
        failed = self.test_results['failed']
        
        self.stdout.write(f"Total tests: {total_tests}")
        self.stdout.write(self.style.SUCCESS(f"Passed: {passed}"))
        
        if failed > 0:
            self.stdout.write(self.style.ERROR(f"Failed: {failed}"))
            self.stdout.write("\nFailed tests:")
            for error in self.test_results['errors']:
                self.stdout.write(self.style.ERROR(f"  - {error}"))
        else:
            self.stdout.write(self.style.SUCCESS("Failed: 0"))
        
        success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        self.stdout.write(f"\nSuccess rate: {success_rate:.1f}%")
        
        if failed == 0:
            self.stdout.write(self.style.SUCCESS("\n✓ All compatibility tests passed!"))
        else:
            self.stdout.write(self.style.ERROR(f"\n✗ {failed} compatibility issues found."))
        
        self.stdout.write('='*60)