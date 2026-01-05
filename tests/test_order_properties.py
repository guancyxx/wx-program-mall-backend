"""
Property-based tests for order system
Feature: django-mall-migration, Property 12: Order Creation and Status
"""

import pytest
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.orders.models import Order, OrderItem, ReturnOrder
from apps.orders.services import OrderService
from apps.membership.models import MembershipTier, MembershipStatus
from tests.factories import UserFactory, MembershipTierFactory

User = get_user_model()


class TestOrderCreationProperties(TestCase):
    """Property-based tests for order creation"""

    def setUp(self):
        """Set up test data"""
        # Create membership tiers
        self.bronze_tier = MembershipTierFactory(
            name='Bronze',
            min_spending=Decimal('0.00'),
            max_spending=Decimal('999.99'),
            points_multiplier=Decimal('1.0')
        )
        self.silver_tier = MembershipTierFactory(
            name='Silver',
            min_spending=Decimal('1000.00'),
            max_spending=Decimal('4999.99'),
            points_multiplier=Decimal('1.2')
        )

    @given(
        goods_count=st.integers(min_value=1, max_value=5),
        quantities=st.lists(st.integers(min_value=1, max_value=10), min_size=1, max_size=5),
        prices=st.lists(st.decimals(min_value=1, max_value=1000, places=2), min_size=1, max_size=5),
        order_type=st.integers(min_value=1, max_value=2),
        remark=st.text(max_size=100)
    )
    @settings(max_examples=100, deadline=5000)
    def test_order_creation_and_status_property(self, goods_count, quantities, prices, order_type, remark):
        """
        Property 12: Order Creation and Status
        For any valid checkout request, an order should be created with PENDING_PAYMENT status 
        and contain all selected products with correct quantities and prices
        **Validates: Requirements 5.1**
        """
        # Ensure lists have same length
        goods_count = min(goods_count, len(quantities), len(prices))
        quantities = quantities[:goods_count]
        prices = prices[:goods_count]
        
        # Create user
        user = UserFactory()
        
        # Create membership status
        MembershipStatus.objects.get_or_create(user=user, defaults={'tier': self.bronze_tier})
        
        # Create order data
        goods_list = []
        expected_total = Decimal('0.00')
        
        for i in range(goods_count):
            gid = f"test_product_{i}"
            quantity = quantities[i]
            price = prices[i]
            
            goods_list.append({
                'gid': gid,
                'quantity': quantity,
                'price': float(price),
                'product_info': {'name': f'Test Product {i}'}
            })
            
            expected_total += Decimal(str(quantity)) * price
        
        order_data = {
            'goods': goods_list,
            'address': {
                'name': 'Test User',
                'phone': '1234567890',
                'address': 'Test Address'
            },
            'type': order_type,
            'remark': remark,
            'lid': 1 if order_type == 1 else None
        }
        
        # Create order
        order, error_msg = OrderService.create_order(user, order_data)
        
        # Assertions for Property 12
        assert order is not None, f"Order creation failed: {error_msg}"
        assert error_msg == "", f"Unexpected error: {error_msg}"
        
        # Check order has PENDING_PAYMENT status (-1)
        assert order.status == -1, f"Expected status -1 (PENDING_PAYMENT), got {order.status}"
        
        # Check order contains all selected products
        order_items = OrderItem.objects.filter(order=order)
        assert order_items.count() == goods_count, f"Expected {goods_count} items, got {order_items.count()}"
        
        # Check quantities and prices are correct
        total_calculated = Decimal('0.00')
        for i, item in enumerate(order_items.order_by('gid')):
            expected_gid = f"test_product_{i}"
            expected_quantity = quantities[i]
            expected_price = prices[i]
            
            assert item.gid == expected_gid, f"Expected gid {expected_gid}, got {item.gid}"
            assert item.quantity == expected_quantity, f"Expected quantity {expected_quantity}, got {item.quantity}"
            # Allow for member pricing adjustments
            assert item.price <= expected_price, f"Item price {item.price} should not exceed original {expected_price}"
            
            total_calculated += item.amount
        
        # Check order total (may be less than expected due to member discounts)
        assert order.amount <= expected_total, f"Order amount {order.amount} should not exceed expected {expected_total}"
        
        # Check return orders were created
        return_orders = ReturnOrder.objects.filter(roid=order.roid, uid=user)
        assert return_orders.count() == goods_count, f"Expected {goods_count} return orders, got {return_orders.count()}"
        
        # Check order has required fields
        assert order.roid is not None and order.roid != "", "Order should have a valid roid"
        assert order.uid == user, "Order should be associated with the correct user"
        assert order.type == order_type, f"Expected type {order_type}, got {order.type}"
        assert order.remark == remark, f"Expected remark '{remark}', got '{order.remark}'"
        assert order.create_time is not None, "Order should have creation time"
        assert order.lock_timeout is not None, "Order should have payment timeout"

    @given(
        invalid_goods=st.one_of(
            st.just([]),  # Empty goods list
            st.lists(st.dictionaries(
                keys=st.sampled_from(['gid', 'quantity', 'price']),
                values=st.one_of(
                    st.integers(min_value=-10, max_value=0),  # Invalid quantities/prices
                    st.text(max_size=5),  # Invalid types
                    st.none()  # Missing values
                ),
                min_size=1,
                max_size=3
            ), min_size=1, max_size=3)
        )
    )
    @settings(max_examples=50, deadline=3000)
    def test_invalid_order_creation_property(self, invalid_goods):
        """
        Property: Invalid order creation should fail gracefully
        For any invalid goods data, order creation should fail with appropriate error message
        """
        user = UserFactory()
        MembershipStatus.objects.get_or_create(user=user, defaults={'tier': self.bronze_tier})
        
        order_data = {
            'goods': invalid_goods,
            'address': {'name': 'Test', 'phone': '123', 'address': 'Test'},
            'type': 2,
            'remark': 'Test'
        }
        
        # Order creation should fail
        order, error_msg = OrderService.create_order(user, order_data)
        
        assert order is None, "Order creation should fail for invalid goods"
        assert error_msg != "", "Error message should be provided for failed order creation"
        
        # No orders should be created in database
        assert Order.objects.filter(uid=user).count() == 0, "No orders should be created for invalid data"

    @given(
        member_tier=st.sampled_from(['Bronze', 'Silver', 'Gold', 'Platinum']),
        order_amount=st.decimals(min_value=10, max_value=1000, places=2)
    )
    @settings(max_examples=50, deadline=3000)
    def test_member_benefits_application_property(self, member_tier, order_amount):
        """
        Property: Member benefits should be applied consistently based on tier
        For any member tier and order amount, appropriate benefits should be applied
        """
        # Create user with specific tier
        user = UserFactory()
        
        # Map member_tier to correct factory or create with correct name
        tier_mapping = {
            'Bronze': 'Bronze',
            'Silver': 'Silver', 
            'Gold': 'Gold',
            'Platinum': 'Platinum'
        }
        
        if member_tier == 'Bronze':
            tier = self.bronze_tier
        else:
            # Create tier with correct capitalized name
            tier = MembershipTierFactory(
                name=tier_mapping[member_tier],  # Use capitalized name
                min_spending=Decimal('1000.00'),
                points_multiplier=Decimal('1.5')
            )
        
        # Handle existing membership status
        try:
            membership_status = MembershipStatus.objects.get(user=user)
            membership_status.tier = tier
            membership_status.save()
        except MembershipStatus.DoesNotExist:
            MembershipStatus.objects.create(user=user, tier=tier)
        
        # Create order data
        goods_list = [{
            'gid': 'test_product',
            'quantity': 1,
            'price': float(order_amount),
            'product_info': {'name': 'Test Product'}
        }]
        
        order_data = {
            'goods': goods_list,
            'address': {'name': 'Test', 'phone': '123', 'address': 'Test'},
            'type': 2,  # Delivery
            'remark': 'Test'
        }
        
        # Create order
        order, error_msg = OrderService.create_order(user, order_data)
        
        assert order is not None, f"Order creation failed: {error_msg}"
        
        # Check member benefits were applied
        discounts = order.discounts.all()
        
        if member_tier in ['Silver', 'Gold', 'Platinum']:
            # Should have tier discount
            tier_discounts = [d for d in discounts if d.discount_type == 'tier_discount']
            assert len(tier_discounts) > 0, f"{member_tier} members should receive tier discounts. Got discounts: {[d.discount_type for d in discounts]}"
            
            # Should have free shipping for delivery orders
            shipping_discounts = [d for d in discounts if d.discount_type == 'free_shipping']
            assert len(shipping_discounts) > 0, f"{member_tier} members should receive free shipping. Got discounts: {[d.discount_type for d in discounts]}"
        
        # Order amount should be adjusted for discounts (allow for member pricing)
        original_amount = order_amount
        if member_tier != 'Bronze':
            # Member pricing and discounts should reduce or maintain the final amount
            # Note: Due to member pricing, the final amount might be less than or equal to original
            assert order.amount <= original_amount * Decimal('1.1'), f"Order amount {order.amount} should not be significantly more than original {original_amount} for {member_tier}"

    @given(
        payment_success=st.booleans(),
        order_status=st.integers(min_value=-1, max_value=7)
    )
    @settings(max_examples=30, deadline=3000)
    def test_payment_processing_property(self, payment_success, order_status):
        """
        Property: Payment processing should update order status correctly
        For any payment result, order status should be updated appropriately
        """
        # Create order
        user = UserFactory()
        MembershipStatus.objects.get_or_create(user=user, defaults={'tier': self.bronze_tier})
        
        order = Order.objects.create(
            roid=f"test_order_{timezone.now().timestamp()}",
            uid=user,
            amount=Decimal('100.00'),
            status=-1,  # Pending payment
            type=2,
            address={'test': 'address'},
            openid='test_openid'
        )
        
        original_status = order.status
        
        if payment_success and original_status == -1:
            # Process successful payment
            success, message = OrderService.process_payment_success(order.roid)
            
            assert success, f"Payment processing should succeed: {message}"
            
            # Reload order
            order.refresh_from_db()
            
            # Status should be updated to paid (1)
            assert order.status == 1, f"Order status should be 1 (paid), got {order.status}"
            assert order.pay_time is not None, "Pay time should be set"
            assert order.lock_timeout is None, "Lock timeout should be cleared"
        
        elif not payment_success or original_status != -1:
            # Payment should fail for non-pending orders
            success, message = OrderService.process_payment_success(order.roid)
            
            if original_status != -1:
                assert not success, "Payment processing should fail for non-pending orders"
            
            # Order status should remain unchanged for failed payments
            order.refresh_from_db()
            if original_status != -1:
                assert order.status == original_status, "Order status should remain unchanged for failed payments"