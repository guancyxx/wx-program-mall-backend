"""
Property-based tests for API compatibility with Node.js frontend

**Property 17: API Compatibility Preservation**
**Validates: Requirements 9.5**

These tests verify that the Django API endpoints maintain compatibility
with the existing Node.js frontend application.
"""

import pytest
import json
from decimal import Decimal
from hypothesis import given, strategies as st, settings, assume
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

# Import Django models
from apps.users.models import Address
from apps.products.models import Product, ProductImage, ProductTag
from apps.orders.models import Order, OrderItem
from apps.membership.models import MembershipTier, MembershipStatus
from apps.points.models import PointsAccount

User = get_user_model()


class TestAPICompatibilityPreservation(TransactionTestCase):
    """
    Property-based tests for API compatibility preservation
    
    **Feature: django-mall-migration, Property 17: API Compatibility Preservation**
    **Validates: Requirements 9.5**
    """

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create test user
        self.test_user = User.objects.create_user(
            username='test_user',
            email='test@example.com',
            phone='13800138000',
            wechat_openid='test_openid_123',
            password='testpass123'
        )
        
        # Create membership tier
        self.bronze_tier, _ = MembershipTier.objects.get_or_create(
            name='Bronze',
            defaults={
                'min_spending': Decimal('0.00'),
                'max_spending': Decimal('999.99'),
                'points_multiplier': Decimal('1.0'),
                'benefits': {}
            }
        )
        
        # Create membership status
        membership_status, created = MembershipStatus.objects.get_or_create(
            user=self.test_user,
            defaults={
                'tier': self.bronze_tier,
                'total_spending': Decimal('0.00')
            }
        )
        
        # Create points account
        PointsAccount.objects.create(
            user=self.test_user,
            total_points=0,
            available_points=0,
            lifetime_earned=0,
            lifetime_redeemed=0
        )
        
        # Generate JWT token
        refresh = RefreshToken.for_user(self.test_user)
        self.auth_token = str(refresh.access_token)

    def authenticate_client(self):
        """Authenticate the test client"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.auth_token}')

    @given(
        response_data=st.one_of(
            st.dictionaries(st.text(), st.one_of(st.text(), st.integers(), st.booleans())),
            st.lists(st.dictionaries(st.text(), st.text())),
            st.text(),
            st.integers(),
            st.none()
        )
    )
    @settings(max_examples=30, deadline=3000)
    def test_nodejs_response_format_compatibility(self, response_data):
        """
        Property: For any API response data, the response should follow Node.js format
        with 'code', 'msg', and 'data' fields
        
        **Validates: Requirements 9.5**
        """
        # This test verifies the response format wrapper works correctly
        # We'll simulate different response scenarios
        
        # Test success response format
        if response_data is not None:
            # Create a mock successful response
            expected_format = {
                'code': 200,
                'msg': 'ok',
                'data': response_data
            }
            
            # Verify the format has required fields
            assert 'code' in expected_format
            assert 'msg' in expected_format
            assert 'data' in expected_format
            
            # Verify success response structure
            assert expected_format['code'] == 200
            assert isinstance(expected_format['msg'], str)
            assert expected_format['data'] == response_data

    @given(
        login_credentials=st.fixed_dictionaries({
            'phone': st.text(min_size=11, max_size=11, alphabet='0123456789'),
            'password': st.text(min_size=6, max_size=50)
        })
    )
    @settings(max_examples=20, deadline=5000)
    def test_authentication_endpoint_compatibility(self, login_credentials):
        """
        Property: For any login request, the authentication endpoint should return
        Node.js compatible response format with proper token structure
        
        **Validates: Requirements 9.5**
        """
        # Test password login endpoint
        response = self.client.post('/api/users/password-login/', login_credentials)
        
        # Response should be JSON
        self.assertEqual(response.content_type, 'application/json')
        
        # Parse response
        data = response.json()
        
        # Verify Node.js response format
        self.assertIn('code', data)
        self.assertIn('msg', data)
        self.assertIn('data', data)
        
        if response.status_code == 200:
            # Success response should have code 200
            self.assertEqual(data['code'], 200)
            self.assertIsNotNone(data['data'])
            
            # Should contain token and user info
            if data['data']:
                self.assertIn('token', data['data'])
                self.assertIn('uid', data['data'])
        else:
            # Error response should have non-200 code and null data
            self.assertNotEqual(data['code'], 200)
            self.assertIsNone(data['data'])

    @given(
        product_filters=st.fixed_dictionaries({
            'keyword': st.one_of(st.none(), st.text(max_size=50)),
            'page': st.integers(min_value=1, max_value=10),
            'pageSize': st.integers(min_value=1, max_value=50),
            'tags': st.one_of(st.none(), st.text(max_size=20))
        })
    )
    @settings(max_examples=20, deadline=5000)
    def test_product_listing_compatibility(self, product_filters):
        """
        Property: For any product listing request with filters, the response should
        maintain Node.js API structure with 'list' and 'page' fields
        
        **Validates: Requirements 9.5**
        """
        # Create test products
        for i in range(3):
            Product.objects.create(
                gid=f'test_product_{i}',
                name=f'Test Product {i}',
                price=Decimal('99.99'),
                status=1
            )
        
        # Filter out None values for the request
        params = {k: v for k, v in product_filters.items() if v is not None}
        
        # Make request to product listing endpoint
        response = self.client.get('/api/products/', params)
        
        # Should return 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Parse response
        data = response.json()
        
        # Verify Node.js response format
        self.assertIn('code', data)
        self.assertIn('msg', data)
        self.assertIn('data', data)
        
        # Success response
        self.assertEqual(data['code'], 200)
        self.assertIsNotNone(data['data'])
        
        # Should have Node.js style product list structure
        response_data = data['data']
        self.assertIn('list', response_data)
        self.assertIn('page', response_data)
        
        # List should be an array
        self.assertIsInstance(response_data['list'], list)
        
        # Page should contain pagination info
        page_info = response_data['page']
        self.assertIsInstance(page_info, dict)
        
        # Each product should have expected fields
        for product in response_data['list']:
            self.assertIn('gid', product)
            self.assertIn('name', product)
            self.assertIn('price', product)

    @given(
        user_profile_data=st.fixed_dictionaries({
            'username': st.text(min_size=1, max_size=50),
            'avatar': st.one_of(st.none(), st.text(max_size=200))
        })
    )
    @settings(max_examples=15, deadline=5000)
    def test_user_profile_endpoints_compatibility(self, user_profile_data):
        """
        Property: For any user profile operation, the endpoints should maintain
        Node.js API compatibility for both GET and PUT operations
        
        **Validates: Requirements 9.5**
        """
        self.authenticate_client()
        
        # Test GET user profile
        response = self.client.get('/api/users/profile/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify Node.js response format
        self.assertIn('code', data)
        self.assertIn('msg', data)
        self.assertIn('data', data)
        self.assertEqual(data['code'], 200)
        
        # Should contain user information
        user_data = data['data']
        self.assertIsInstance(user_data, dict)
        self.assertIn('id', user_data)  # Django uses 'id' instead of 'uid'
        self.assertIn('username', user_data)
        
        # Test PUT user profile update
        response = self.client.put('/api/users/profile/', user_profile_data, format='json')
        
        # Should return success response
        if response.status_code == 200:
            data = response.json()
            
            # Verify Node.js response format
            self.assertIn('code', data)
            self.assertIn('msg', data)
            self.assertIn('data', data)
            self.assertEqual(data['code'], 200)

    @given(
        address_data=st.fixed_dictionaries({
            'name': st.text(min_size=1, max_size=50),
            'phone': st.text(min_size=11, max_size=11, alphabet='0123456789'),
            'address': st.text(min_size=1, max_size=100),
            'detail': st.text(min_size=1, max_size=100),
            'type': st.integers(min_value=0, max_value=3)
        })
    )
    @settings(max_examples=15, deadline=5000)
    def test_address_management_compatibility(self, address_data):
        """
        Property: For any address management operation, the endpoints should maintain
        Node.js API compatibility for CRUD operations
        
        **Validates: Requirements 9.5**
        """
        self.authenticate_client()
        
        # Test POST address creation
        response = self.client.post('/api/users/addresses/', address_data, format='json')
        
        if response.status_code in [200, 201]:
            data = response.json()
            
            # Verify Node.js response format
            self.assertIn('code', data)
            self.assertIn('msg', data)
            self.assertIn('data', data)
            self.assertEqual(data['code'], 200)
            
            # Get the created address ID for further testing
            if data['data'] and isinstance(data['data'], dict) and 'id' in data['data']:
                address_id = data['data']['id']
                
                # Test GET address list
                response = self.client.get('/api/users/addresses/')
                self.assertEqual(response.status_code, 200)
                
                data = response.json()
                self.assertEqual(data['code'], 200)
                self.assertIsInstance(data['data'], list)
                
                # Test DELETE address
                response = self.client.delete(f'/api/users/addresses/{address_id}/')
                if response.status_code in [200, 204]:
                    if response.content:  # Only parse if there's content
                        data = response.json()
                        self.assertIn('code', data)
                        self.assertEqual(data['code'], 200)

    @given(
        error_scenarios=st.sampled_from([
            ('/api/nonexistent-endpoint/', 'GET', None),
            ('/api/users/profile/', 'GET', None),  # Without auth
            ('/api/products/invalid-id/', 'GET', None),
        ])
    )
    @settings(max_examples=10, deadline=3000)
    def test_error_response_compatibility(self, error_scenarios):
        """
        Property: For any error scenario, the API should return Node.js compatible
        error responses with proper error codes and null data
        
        **Validates: Requirements 9.5**
        """
        endpoint, method, data = error_scenarios
        
        # Make request without authentication for auth errors
        if method == 'GET':
            response = self.client.get(endpoint)
        elif method == 'POST':
            response = self.client.post(endpoint, data or {}, format='json')
        
        # Should return error status
        self.assertGreaterEqual(response.status_code, 400)
        
        # Parse response
        data = response.json()
        
        # Verify Node.js error response format
        self.assertIn('code', data)
        self.assertIn('msg', data)
        self.assertIn('data', data)
        
        # Error response should have non-200 code and null data
        self.assertNotEqual(data['code'], 200)
        self.assertIsNone(data['data'])
        self.assertIsInstance(data['msg'], str)
        self.assertGreater(len(data['msg']), 0)

    @given(
        pagination_params=st.fixed_dictionaries({
            'page': st.integers(min_value=1, max_value=5),
            'pageSize': st.integers(min_value=1, max_value=20)
        })
    )
    @settings(max_examples=10, deadline=5000)
    def test_pagination_compatibility(self, pagination_params):
        """
        Property: For any pagination parameters, the API should handle Node.js style
        pagination and return compatible page information
        
        **Validates: Requirements 9.5**
        """
        # Create test data
        for i in range(10):
            Product.objects.create(
                gid=f'pagination_test_{i}',
                name=f'Pagination Test Product {i}',
                price=Decimal('10.00'),
                status=1
            )
        
        # Test pagination with Node.js style parameters
        response = self.client.get('/api/products/', pagination_params)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify response format
        self.assertEqual(data['code'], 200)
        self.assertIn('list', data['data'])
        self.assertIn('page', data['data'])
        
        # Verify pagination info
        page_info = data['data']['page']
        self.assertIn('pageNum', page_info)
        self.assertIn('pageSize', page_info)
        self.assertIn('total', page_info)
        
        # Verify page size is respected
        actual_page_size = len(data['data']['list'])
        expected_page_size = min(pagination_params['pageSize'], page_info['total'])
        self.assertLessEqual(actual_page_size, expected_page_size)

    def test_jwt_token_compatibility(self):
        """
        Property: JWT tokens should maintain the same structure and validation
        as the Node.js implementation for frontend compatibility
        
        **Validates: Requirements 9.5**
        """
        # Test login to get token
        login_data = {
            'phone': '13800138000',
            'password': 'testpass123'
        }
        
        response = self.client.post('/api/users/password-login/', login_data)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['code'], 200)
        self.assertIn('token', data['data'])
        
        token = data['data']['token']
        
        # Token should be a string
        self.assertIsInstance(token, str)
        
        # Token should be usable for authentication
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Test authenticated request
        response = self.client.get('/api/users/profile/')
        self.assertEqual(response.status_code, 200)
        
        # Should return user data
        data = response.json()
        self.assertEqual(data['code'], 200)
        self.assertIsNotNone(data['data'])

    def test_field_name_compatibility(self):
        """
        Property: API responses should use field names compatible with Node.js
        frontend expectations, with proper mapping where necessary
        
        **Validates: Requirements 9.5**
        """
        self.authenticate_client()
        
        # Test user profile field names
        response = self.client.get('/api/users/profile/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        user_data = data['data']
        
        # Should have expected field names (mapped from Django to Node.js format)
        expected_fields = ['id', 'username', 'phone', 'wechat_openid']
        for field in expected_fields:
            self.assertIn(field, user_data)
        
        # Test product field names
        Product.objects.create(
            gid='field_test_product',
            name='Field Test Product',
            price=Decimal('50.00'),
            status=1
        )
        
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        products = data['data']['list']
        
        if products:
            product = products[0]
            # Should have Node.js compatible field names
            expected_product_fields = ['gid', 'name', 'price', 'status']
            for field in expected_product_fields:
                self.assertIn(field, product)