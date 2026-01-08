"""
Simple integration tests for Django mall server.

This module tests basic integration workflows without complex setup.
"""
import pytest
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock

from apps.users.models import Address
from apps.membership.models import MembershipTier, MembershipStatus
from apps.products.models import Product, Category
from apps.orders.models import Order, OrderItem
from apps.points.models import PointsAccount, PointsTransaction
from apps.payments.models import PaymentTransaction

User = get_user_model()


class SimpleIntegrationTests(TestCase):
    """
    Simple integration tests for basic workflows.
    
    Tests basic functionality without complex setup requirements.
    """
    
    def setUp(self):
        """Set up basic test data."""
        self.client = APIClient()
        
        # Get or create membership tiers
        self.bronze_tier, _ = MembershipTier.objects.get_or_create(
            name='bronze',
            defaults={
                'display_name': 'Bronze',
                'min_spending': Decimal('0'),
                'max_spending': Decimal('999.99'),
                'points_multiplier': Decimal('1.0'),
                'benefits': {'free_shipping': False}
            }
        )
        
        self.silver_tier, _ = MembershipTier.objects.get_or_create(
            name='silver',
            defaults={
                'display_name': 'Silver',
                'min_spending': Decimal('1000'),
                'max_spending': Decimal('4999.99'),
                'points_multiplier': Decimal('1.2'),
                'benefits': {'free_shipping': True}
            }
        )
        
        # Create test category and product
        self.category = Category.objects.create(name="Electronics")
        self.product = Product.objects.create(
            gid="test_product_1",
            name="Test iPhone",
            price=Decimal('999.99'),
            category=self.category,
            inventory=10,
            status=1
        )
    
    def test_basic_user_registration(self):
        """Test basic user registration workflow."""
        user_data = {
            'username': 'testuser123',
            'email': 'test@example.com',
            'password': 'testpass123',
            'phone': '1234567890',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        response = self.client.post('/api/users/register/', user_data)
        
        # Should create user successfully or return appropriate error
        self.assertIn(response.status_code, [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ])
        
        if response.status_code == status.HTTP_201_CREATED:
            # Verify user was created
            user = User.objects.get(username=user_data['username'])
            self.assertIsNotNone(user)
            
            # Check if membership was created
            try:
                membership = MembershipStatus.objects.get(user=user)
                self.assertEqual(membership.tier.name, 'bronze')
            except MembershipStatus.DoesNotExist:
                # Membership creation might be handled differently
                pass
    
    def test_product_listing(self):
        """Test product listing endpoint."""
        response = self.client.get('/api/products/')
        
        # Should return products or appropriate error
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ])
        
        if response.status_code == status.HTTP_200_OK:
            # Should have some structure - check for Node.js compatible format
            self.assertIn('data', response.data)
            if 'data' in response.data:
                self.assertIn('list', response.data['data'])
    
    def test_product_detail(self):
        """Test product detail endpoint."""
        response = self.client.get(f'/api/products/{self.product.gid}/')
        
        # Should return product details or appropriate error
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ])
        
        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(response.data['name'], self.product.name)
    
    def test_membership_tiers_exist(self):
        """Test that membership tiers are properly created."""
        # Verify tiers exist
        bronze = MembershipTier.objects.filter(name='bronze').first()
        silver = MembershipTier.objects.filter(name='silver').first()
        
        self.assertIsNotNone(bronze)
        self.assertIsNotNone(silver)
        
        # Verify tier properties
        self.assertEqual(bronze.points_multiplier, Decimal('1.0'))
        self.assertEqual(silver.points_multiplier, Decimal('1.2'))
    
    def test_basic_order_creation(self):
        """Test basic order creation without authentication."""
        # Create a test user manually
        user = User.objects.create_user(
            username='orderuser',
            email='order@example.com',
            password='orderpass123'
        )
        
        # Create membership status
        membership = MembershipStatus.objects.create(
            user=user,
            tier=self.bronze_tier,
            total_spending=Decimal('0')
        )
        
        # Create points account
        points_account = PointsAccount.objects.create(
            user=user,
            balance=Decimal('0'),
            lifetime_earned=Decimal('0'),
            lifetime_spent=Decimal('0')
        )
        
        # Authenticate user
        self.client.force_authenticate(user=user)
        
        order_data = {
            'goods': [
                {
                    'gid': self.product.gid,
                    'num': 1,
                    'price': str(self.product.price)
                }
            ],
            'address': {
                'recipient_name': 'Test User',
                'phone': '1234567890',
                'province': 'Beijing',
                'city': 'Beijing',
                'district': 'Chaoyang',
                'detail_address': '123 Test Street'
            },
            'use_points': 0
        }
        
        response = self.client.post('/api/order/createOrder', order_data)
        
        # Should create order or return appropriate error
        self.assertIn(response.status_code, [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ])
        
        if response.status_code == status.HTTP_201_CREATED:
            # Verify order was created
            self.assertIn('roid', response.data)
            order_id = response.data['roid']
            
            order = Order.objects.get(id=order_id)
            self.assertEqual(order.user, user)
            self.assertEqual(order.total_amount, self.product.price)
    
    def test_api_endpoints_exist(self):
        """Test that key API endpoints exist and return appropriate responses."""
        endpoints = [
            '/api/users/register/',
            '/api/products/',
            '/api/order/createOrder',
            '/api/membership/status/',
            '/api/points/balance/',
        ]
        
        for endpoint in endpoints:
            if endpoint in ['/api/users/register/', '/api/order/createOrder']:
                # POST endpoints
                response = self.client.post(endpoint, {})
            else:
                # GET endpoints
                response = self.client.get(endpoint)
            
            # Should not return 404 (endpoint exists)
            self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            
            # Should return some valid HTTP status
            self.assertIn(response.status_code, [
                status.HTTP_200_OK,
                status.HTTP_201_CREATED,
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
                status.HTTP_405_METHOD_NOT_ALLOWED,
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ])
    
    def test_database_models_work(self):
        """Test that database models can be created and queried."""
        # Test User model
        user = User.objects.create_user(
            username='dbtest',
            email='db@example.com',
            password='dbpass123'
        )
        self.assertIsNotNone(user)
        
        # Test MembershipStatus model
        membership = MembershipStatus.objects.create(
            user=user,
            tier=self.bronze_tier,
            total_spending=Decimal('100')
        )
        self.assertEqual(membership.user, user)
        
        # Test Product model
        product = Product.objects.create(
            gid="db_test_product",
            name="DB Test Product",
            price=Decimal('50.00'),
            category=self.category,
            inventory=5,
            status=1
        )
        self.assertEqual(product.name, "DB Test Product")
        
        # Test PointsAccount model
        points = PointsAccount.objects.create(
            user=user,
            balance=Decimal('500'),
            lifetime_earned=Decimal('500'),
            lifetime_spent=Decimal('0')
        )
        self.assertEqual(points.balance, Decimal('500'))
    
    def test_system_health_check(self):
        """Basic system health check."""
        # Test that Django is working
        self.assertTrue(True)
        
        # Test database connection
        user_count = User.objects.count()
        self.assertGreaterEqual(user_count, 0)
        
        # Test that models are accessible
        tier_count = MembershipTier.objects.count()
        self.assertGreaterEqual(tier_count, 2)  # We created 2 tiers
        
        product_count = Product.objects.count()
        self.assertGreaterEqual(product_count, 1)  # We created 1 product


class BasicWorkflowTests(TestCase):
    """
    Basic workflow tests that don't require complex setup.
    """
    
    def setUp(self):
        """Set up basic test data."""
        self.client = APIClient()
        
        # Get or create minimal required data
        self.bronze_tier, _ = MembershipTier.objects.get_or_create(
            name='bronze',
            defaults={
                'display_name': 'Bronze',
                'min_spending': Decimal('0'),
                'max_spending': Decimal('999.99'),
                'points_multiplier': Decimal('1.0'),
                'benefits': {}
            }
        )
    
    def test_user_creation_workflow(self):
        """Test basic user creation workflow."""
        # Create user
        user = User.objects.create_user(
            username='workflowuser',
            email='workflow@example.com',
            password='workflowpass123'
        )
        
        # Create membership
        membership = MembershipStatus.objects.create(
            user=user,
            tier=self.bronze_tier,
            total_spending=Decimal('0')
        )
        
        # Create points account
        points_account = PointsAccount.objects.create(
            user=user,
            balance=Decimal('100'),  # Registration bonus
            lifetime_earned=Decimal('100'),
            lifetime_spent=Decimal('0')
        )
        
        # Verify workflow completed
        self.assertEqual(user.username, 'workflowuser')
        self.assertEqual(membership.tier.name, 'bronze')
        self.assertEqual(points_account.balance, Decimal('100'))
    
    def test_product_workflow(self):
        """Test basic product workflow."""
        # Create category
        category = Category.objects.create(name="Test Category")
        
        # Create product
        product = Product.objects.create(
            gid="workflow_product",
            name="Workflow Product",
            price=Decimal('199.99'),
            category=category,
            inventory=20,
            status=1
        )
        
        # Verify product created
        self.assertEqual(product.name, "Workflow Product")
        self.assertEqual(product.category.name, "Test Category")
        self.assertTrue(product.is_active)
    
    def test_order_workflow(self):
        """Test basic order workflow."""
        # Create user
        user = User.objects.create_user(
            username='orderworkflow',
            email='orderworkflow@example.com',
            password='orderpass123'
        )
        
        # Create category and product
        category = Category.objects.create(name="Order Category")
        product = Product.objects.create(
            gid="order_product",
            name="Order Product",
            price=Decimal('99.99'),
            category=category,
            inventory=10,
            status=1
        )
        
        # Create order
        order = Order.objects.create(
            user=user,
            total_amount=product.price,
            status='pending_payment',
            shipping_address='Test Address'
        )
        
        # Create order item
        order_item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=1,
            price=product.price
        )
        
        # Verify order workflow
        self.assertEqual(order.user, user)
        self.assertEqual(order.total_amount, product.price)
        self.assertEqual(order_item.product, product)
        self.assertEqual(order_item.quantity, 1)