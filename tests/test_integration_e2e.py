"""
End-to-end integration tests for Django mall server.

This module tests complete user workflows including:
- User registration and login workflows
- WeChat integration functionality  
- Order processing with payment callbacks
- Membership tier upgrades and points system

Requirements: All requirements
"""
import pytest
import json
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
from tests.factories import (
    UserFactory, ProductFactory, CategoryFactory,
    create_user_with_membership, create_all_membership_tiers
)

User = get_user_model()


class EndToEndIntegrationTests(TransactionTestCase):
    """
    End-to-end integration tests for complete user workflows.
    
    Tests complete user registration and login workflows, verifies WeChat integration
    functionality, tests order processing with payment callbacks, and validates
    membership tier upgrades and points system.
    """
    
    def setUp(self):
        """Set up test data for integration tests."""
        self.client = APIClient()
        
        # Create membership tiers
        self.tiers = create_all_membership_tiers()
        
        # Create test category and products
        self.category = CategoryFactory(name="Electronics")
        self.product1 = ProductFactory(
            name="iPhone 15",
            price=Decimal('999.99'),
            category=self.category,
            inventory=10
        )
        self.product2 = ProductFactory(
            name="MacBook Pro",
            price=Decimal('2499.99'),
            category=self.category,
            inventory=5
        )
        
        # Test user data
        self.user_data = {
            'username': 'testuser123',
            'email': 'test@example.com',
            'password': 'testpass123',
            'phone': '1234567890',
            'first_name': 'Test',
            'last_name': 'User'
        }
    
    def test_complete_user_registration_workflow(self):
        """
        Test complete user registration and login workflow.
        
        Tests:
        - User registration with default Bronze membership
        - User login and token generation
        - Profile management
        - Address management
        """
        # Step 1: User registration
        response = self.client.post('/api/users/register/', self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify user was created with Bronze membership
        user = User.objects.get(username=self.user_data['username'])
        self.assertIsNotNone(user)
        
        membership = MembershipStatus.objects.get(user=user)
        self.assertEqual(membership.tier.name, 'bronze')
        
        # Verify points account was created
        points_account = PointsAccount.objects.get(user=user)
        self.assertEqual(points_account.available_points, 100)  # Registration bonus
        
        # Step 2: User login
        login_data = {
            'username': self.user_data['username'],
            'password': self.user_data['password']
        }
        response = self.client.post('/api/users/passwordLogin/', login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Extract token and set authentication
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Step 3: Profile management
        response = self.client.get('/api/users/getUserInfo/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.user_data['username'])
        
        # Update profile
        update_data = {'first_name': 'Updated', 'last_name': 'Name'}
        response = self.client.put('/api/users/modifyInfo/', update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Step 4: Address management
        address_data = {
            'recipient_name': 'Test User',
            'phone': '1234567890',
            'province': 'Beijing',
            'city': 'Beijing',
            'district': 'Chaoyang',
            'detail_address': '123 Test Street',
            'is_default': True
        }
        response = self.client.post('/api/users/addAddress/', address_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify address was created
        address = Address.objects.get(user=user)
        self.assertEqual(address.recipient_name, address_data['recipient_name'])
    
    @patch('apps.common.wechat.WeChatAPI.get_user_info')
    @patch('apps.common.wechat.WeChatAPI.code2session')
    def test_wechat_integration_workflow(self, mock_code2session, mock_get_user_info):
        """
        Test WeChat integration functionality.
        
        Tests:
        - WeChat OAuth login
        - User info retrieval from WeChat
        - WeChat openid storage
        """
        # Mock WeChat API responses
        mock_code2session.return_value = {
            'openid': 'test_openid_123',
            'session_key': 'test_session_key',
            'unionid': 'test_unionid'
        }
        
        mock_get_user_info.return_value = {
            'nickName': 'WeChat User',
            'avatarUrl': 'https://example.com/avatar.jpg',
            'gender': 1,
            'city': 'Beijing',
            'province': 'Beijing',
            'country': 'China'
        }
        
        # Step 1: WeChat login
        wechat_data = {
            'code': 'test_wechat_code',
            'userInfo': {
                'nickName': 'WeChat User',
                'avatarUrl': 'https://example.com/avatar.jpg'
            }
        }
        
        response = self.client.post('/api/users/login/', wechat_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify user was created with WeChat info
        user = User.objects.get(wechat_openid='test_openid_123')
        self.assertIsNotNone(user)
        
        # Verify membership and points account created
        membership = MembershipStatus.objects.get(user=user)
        self.assertEqual(membership.tier.name, 'bronze')
        
        points_account = PointsAccount.objects.get(user=user)
        self.assertEqual(points_account.balance, Decimal('100'))  # Registration bonus
    
    def test_complete_order_processing_workflow(self):
        """
        Test complete order processing with payment callbacks.
        
        Tests:
        - Order creation
        - Payment processing
        - Inventory updates
        - Points award
        - Membership tier upgrade
        """
        # Create user with some spending history
        user, membership = create_user_with_membership('bronze', 500)
        
        # Authenticate user
        self.client.force_authenticate(user=user)
        
        # Step 1: Create order
        order_data = {
            'goods': [
                {
                    'gid': self.product1.id,
                    'num': 2,
                    'price': str(self.product1.price)
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
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        order_id = response.data['roid']
        order = Order.objects.get(id=order_id)
        
        # Verify order was created correctly
        self.assertEqual(order.status, 'pending_payment')
        self.assertEqual(order.total_amount, Decimal('1999.98'))  # 2 * 999.99
        
        # Verify order items
        order_items = OrderItem.objects.filter(order=order)
        self.assertEqual(order_items.count(), 1)
        self.assertEqual(order_items.first().quantity, 2)
        
        # Step 2: Simulate payment callback
        payment_data = {
            'out_trade_no': str(order_id),
            'transaction_id': 'wx_test_transaction_123',
            'total_fee': '199998',  # In cents
            'result_code': 'SUCCESS',
            'return_code': 'SUCCESS'
        }
        
        response = self.client.post('/api/order/callback', payment_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify order status updated
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        
        # Verify payment transaction created
        payment = PaymentTransaction.objects.get(order=order)
        self.assertEqual(payment.status, 'completed')
        self.assertEqual(payment.transaction_id, 'wx_test_transaction_123')
        
        # Step 3: Verify inventory updated
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.inventory, 8)  # 10 - 2
        
        # Step 4: Verify points awarded
        points_account = PointsAccount.objects.get(user=user)
        # Should have registration bonus (100) + order points (1999.98 * 1.0 = 1999)
        expected_points = Decimal('100') + Decimal('200') + Decimal('1999')  # reg + first purchase + order
        self.assertEqual(points_account.balance, expected_points)
        
        # Verify points transaction created
        transactions = PointsTransaction.objects.filter(account=points_account, transaction_type='earned')
        self.assertTrue(transactions.exists())
        
        # Step 5: Verify membership tier upgrade
        membership.refresh_from_db()
        # Total spending should be 500 + 1999.98 = 2499.98 (Silver tier)
        self.assertEqual(membership.total_spending, Decimal('2499.98'))
        self.assertEqual(membership.tier.name, 'silver')
    
    def test_membership_tier_upgrade_workflow(self):
        """
        Test membership tier upgrades and points system.
        
        Tests:
        - Automatic tier upgrades based on spending
        - Points multiplier changes
        - Tier benefits application
        """
        # Create Bronze user
        user, membership = create_user_with_membership('bronze', 0)
        self.client.force_authenticate(user=user)
        
        # Create multiple orders to trigger tier upgrades
        orders_data = [
            {'amount': Decimal('600'), 'expected_tier': 'bronze'},
            {'amount': Decimal('500'), 'expected_tier': 'silver'},  # Total: 1100
            {'amount': Decimal('4000'), 'expected_tier': 'gold'},   # Total: 5100
            {'amount': Decimal('15000'), 'expected_tier': 'platinum'} # Total: 20100
        ]
        
        for i, order_data in enumerate(orders_data):
            # Create order
            order = Order.objects.create(
                user=user,
                total_amount=order_data['amount'],
                status='pending_payment'
            )
            
            # Simulate payment completion
            from apps.orders.services import OrderService
            OrderService.complete_payment(order, f'tx_{i}')
            
            # Verify tier upgrade
            membership.refresh_from_db()
            self.assertEqual(membership.tier.name, order_data['expected_tier'])
            
            # Verify points multiplier applied
            points_account = PointsAccount.objects.get(user=user)
            tier = membership.tier
            
            # Calculate expected points for this order
            order_points = order_data['amount'] * tier.points_multiplier
            
            # Verify points were awarded with correct multiplier
            last_transaction = PointsTransaction.objects.filter(
                account=points_account,
                transaction_type='earned'
            ).last()
            
            if last_transaction:
                self.assertGreaterEqual(last_transaction.amount, order_points)
    
    def test_points_redemption_workflow(self):
        """
        Test points earning and redemption workflow.
        
        Tests:
        - Points earning from purchases
        - Points redemption for discounts
        - Points balance updates
        - Transaction history
        """
        # Create user with points
        user, membership = create_user_with_membership('silver', 1000)
        points_account = PointsAccount.objects.get(user=user)
        points_account.balance = Decimal('2000')  # Give user 2000 points
        points_account.save()
        
        self.client.force_authenticate(user=user)
        
        # Step 1: Create order with points redemption
        order_data = {
            'goods': [
                {
                    'gid': self.product1.id,
                    'num': 1,
                    'price': str(self.product1.price)
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
            'use_points': 1000  # Redeem 1000 points ($10 discount)
        }
        
        response = self.client.post('/api/order/createOrder', order_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        order_id = response.data['roid']
        order = Order.objects.get(id=order_id)
        
        # Verify discount applied
        expected_total = self.product1.price - Decimal('10')  # $10 discount
        self.assertEqual(order.total_amount, expected_total)
        
        # Verify points deducted
        points_account.refresh_from_db()
        self.assertEqual(points_account.balance, Decimal('1000'))  # 2000 - 1000
        
        # Verify redemption transaction created
        redemption_transaction = PointsTransaction.objects.filter(
            account=points_account,
            transaction_type='spent'
        ).first()
        self.assertIsNotNone(redemption_transaction)
        self.assertEqual(redemption_transaction.amount, Decimal('1000'))
        
        # Step 2: Complete payment and verify points earned
        payment_data = {
            'out_trade_no': str(order_id),
            'transaction_id': 'wx_test_transaction_456',
            'total_fee': str(int(expected_total * 100)),  # In cents
            'result_code': 'SUCCESS',
            'return_code': 'SUCCESS'
        }
        
        response = self.client.post('/api/order/callback', payment_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify points earned from purchase (with Silver multiplier 1.2x)
        points_account.refresh_from_db()
        earned_points = expected_total * Decimal('1.2')  # Silver tier multiplier
        expected_balance = Decimal('1000') + earned_points
        self.assertEqual(points_account.balance, expected_balance)
    
    def test_member_exclusive_features_workflow(self):
        """
        Test member-exclusive features and benefits.
        
        Tests:
        - Tier-based product access
        - Member-specific discounts
        - Free shipping benefits
        - Early access features
        """
        # Create Gold member
        user, membership = create_user_with_membership('gold', 10000)
        self.client.force_authenticate(user=user)
        
        # Create member-exclusive product
        exclusive_product = ProductFactory(
            name="Gold Member Exclusive",
            price=Decimal('199.99'),
            category=self.category,
            is_member_exclusive=True,
            min_tier_required=self.tiers['gold']
        )
        
        # Step 1: Test member-exclusive product access
        response = self.client.get('/api/goods/member-exclusive/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify Gold member can see exclusive products
        product_ids = [p['id'] for p in response.data['results']]
        self.assertIn(exclusive_product.id, product_ids)
        
        # Step 2: Test tier-based benefits in order
        order_data = {
            'goods': [
                {
                    'gid': exclusive_product.id,
                    'num': 1,
                    'price': str(exclusive_product.price)
                }
            ],
            'address': {
                'recipient_name': 'Gold Member',
                'phone': '1234567890',
                'province': 'Beijing',
                'city': 'Beijing',
                'district': 'Chaoyang',
                'detail_address': '123 Test Street'
            },
            'use_points': 0
        }
        
        response = self.client.post('/api/order/createOrder', order_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        order = Order.objects.get(id=response.data['roid'])
        
        # Verify Gold member benefits applied (free shipping, etc.)
        # This would depend on the specific implementation of member benefits
        self.assertEqual(order.shipping_fee, Decimal('0'))  # Free shipping for Gold+
        
        # Step 3: Test lower tier member cannot access exclusive product
        bronze_user, _ = create_user_with_membership('bronze', 0)
        self.client.force_authenticate(user=bronze_user)
        
        response = self.client.get('/api/goods/member-exclusive/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Bronze member should not see Gold-exclusive products
        product_ids = [p['id'] for p in response.data['results']]
        self.assertNotIn(exclusive_product.id, product_ids)
    
    def test_error_handling_and_edge_cases(self):
        """
        Test error handling and edge cases in integration workflows.
        
        Tests:
        - Invalid order data
        - Insufficient inventory
        - Payment failures
        - Invalid authentication
        """
        user, membership = create_user_with_membership('bronze', 0)
        self.client.force_authenticate(user=user)
        
        # Test 1: Order with insufficient inventory
        order_data = {
            'goods': [
                {
                    'gid': self.product1.id,
                    'num': 20,  # More than available stock (10)
                    'price': str(self.product1.price)
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
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('insufficient inventory', response.data['error']['message'].lower())
        
        # Test 2: Order with insufficient points
        points_account = PointsAccount.objects.get(user=user)
        points_account.balance = Decimal('100')  # Only 100 points
        points_account.save()
        
        order_data['goods'][0]['num'] = 1  # Fix inventory issue
        order_data['use_points'] = 1000  # Try to use more points than available
        
        response = self.client.post('/api/order/createOrder', order_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('insufficient points', response.data['error']['message'].lower())
        
        # Test 3: Invalid payment callback
        # First create a valid order
        order_data['use_points'] = 0
        response = self.client.post('/api/order/createOrder', order_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        order_id = response.data['roid']
        
        # Send invalid payment callback
        invalid_payment_data = {
            'out_trade_no': str(order_id),
            'transaction_id': 'invalid_tx',
            'total_fee': '999999',  # Wrong amount
            'result_code': 'FAIL',
            'return_code': 'FAIL'
        }
        
        response = self.client.post('/api/order/callback', invalid_payment_data)
        # Should handle gracefully without crashing
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK])
        
        # Verify order status unchanged
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.status, 'pending_payment')
    
    def test_concurrent_operations(self):
        """
        Test concurrent operations and race conditions.
        
        Tests:
        - Concurrent order creation
        - Inventory race conditions
        - Points balance consistency
        """
        from threading import Thread
        import time
        
        # Create multiple users
        users = []
        for i in range(3):
            user, _ = create_user_with_membership('bronze', 0)
            users.append(user)
        
        # Set product stock to limited amount
        self.product1.inventory = 2
        self.product1.save()
        
        results = []
        
        def create_order_for_user(user):
            """Helper function to create order for a user."""
            client = APIClient()
            client.force_authenticate(user=user)
            
            order_data = {
                'goods': [
                    {
                        'gid': self.product1.id,
                        'num': 1,
                        'price': str(self.product1.price)
                    }
                ],
                'address': {
                    'recipient_name': f'User {user.id}',
                    'phone': '1234567890',
                    'province': 'Beijing',
                    'city': 'Beijing',
                    'district': 'Chaoyang',
                    'detail_address': '123 Test Street'
                },
                'use_points': 0
            }
            
            response = client.post('/api/order/createOrder', order_data)
            results.append((user.id, response.status_code, response.data))
        
        # Create threads for concurrent order creation
        threads = []
        for user in users:
            thread = Thread(target=create_order_for_user, args=(user,))
            threads.append(thread)
        
        # Start all threads simultaneously
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        successful_orders = [r for r in results if r[1] == status.HTTP_201_CREATED]
        failed_orders = [r for r in results if r[1] != status.HTTP_201_CREATED]
        
        # Should have exactly 2 successful orders (matching stock quantity)
        self.assertEqual(len(successful_orders), 2)
        self.assertEqual(len(failed_orders), 1)
        
        # Verify inventory is correctly updated
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.inventory, 0)
        
        # Verify failed order got appropriate error message
        failed_result = failed_orders[0]
        self.assertIn('insufficient inventory', failed_result[2]['error']['message'].lower())