"""
Simple test to debug order member benefits
"""

from django.test import TestCase
from decimal import Decimal
from django.contrib.auth import get_user_model

from apps.orders.models import Order, OrderDiscount
from apps.orders.services import OrderService
from apps.membership.models import MembershipTier, MembershipStatus
from tests.factories import UserFactory

User = get_user_model()


class SimpleOrderTest(TestCase):
    """Simple test for order member benefits"""

    def test_silver_member_benefits(self):
        """Test that Silver members get benefits"""
        # Create Silver tier
        silver_tier = MembershipTier.objects.create(
            name='Silver',
            min_spending=Decimal('1000.00'),
            max_spending=Decimal('4999.99'),
            points_multiplier=Decimal('1.2')
        )
        
        # Create user with Silver membership
        user = UserFactory()
        
        # Check if user already has membership status and update it
        try:
            membership_status = MembershipStatus.objects.get(user=user)
            membership_status.tier = silver_tier
            membership_status.save()
        except MembershipStatus.DoesNotExist:
            MembershipStatus.objects.create(user=user, tier=silver_tier)
        
        # Create order data
        order_data = {
            'goods': [{
                'gid': 'test_product',
                'quantity': 1,
                'price': 100.00,
                'product_info': {'name': 'Test Product'}
            }],
            'address': {'name': 'Test', 'phone': '123', 'address': 'Test'},
            'type': 2,  # Delivery
            'remark': 'Test'
        }
        
        # Create order
        order, error_msg = OrderService.create_order(user, order_data)
        
        print(f"Order created: {order}")
        print(f"Error: {error_msg}")
        
        if order:
            print(f"Order amount: {order.amount}")
            discounts = OrderDiscount.objects.filter(order=order)
            print(f"Discounts count: {discounts.count()}")
            for discount in discounts:
                print(f"Discount: {discount.discount_type} - {discount.discount_amount}")
        
        # Assertions
        self.assertIsNotNone(order, f"Order creation failed: {error_msg}")
        
        # Check discounts
        discounts = OrderDiscount.objects.filter(order=order)
        tier_discounts = discounts.filter(discount_type='tier_discount')
        shipping_discounts = discounts.filter(discount_type='free_shipping')
        
        self.assertGreater(tier_discounts.count(), 0, "Silver members should get tier discount")
        self.assertGreater(shipping_discounts.count(), 0, "Silver members should get free shipping")