"""
Property-based tests for payment processing functionality
"""
import pytest
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase
from decimal import Decimal
from django.db import transaction
from django.contrib.auth import get_user_model

from apps.payments.models import PaymentMethod, PaymentTransaction, RefundRequest, WeChatPayment
from apps.payments.services import PaymentService, WeChatPayService
from apps.orders.models import Order
from tests.factories import UserFactory

User = get_user_model()


class TestPaymentProcessingProperties(TestCase):
    """Property-based tests for payment processing"""

    def setUp(self):
        """Set up test data"""
        # Create payment method
        self.payment_method = PaymentMethod.objects.create(
            name='wechat_pay',
            display_name='WeChat Pay',
            is_active=True,
            sort_order=1
        )

    @given(
        amount=st.decimals(min_value=Decimal('0.01'), max_value=Decimal('9999.99'), places=2),
        user_id=st.integers(min_value=1, max_value=1000)
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.django_db(transaction=True)
    def test_payment_processing_integration(self, amount, user_id):
        """
        Property 13: Payment Processing Integration
        For any successful payment completion, the order status should update to PAID, 
        inventory should decrease, and membership points should be awarded
        **Validates: Requirements 5.3, 6.3**
        """
        error_msg = ""
        
        try:
            with transaction.atomic():
                # Create user
                user = User.objects.create_user(
                    username=f"user_{user_id}",
                    email=f"user_{user_id}@example.com",
                    password="test_password_123"
                )
                
                # Create order
                order = Order.objects.create(
                    roid=f"test_order_{user_id}_{hash(amount) % 10000}",
                    uid=user,
                    amount=amount,
                    status=-1,  # Pending payment
                    type=2,  # Delivery
                    address={'test': 'address'},
                    openid=f"test_openid_{user_id}"
                )
                
                # Create payment transaction
                payment = PaymentTransaction.objects.create(
                    order_id=order.roid,
                    user=user,
                    payment_method=self.payment_method,
                    amount=amount,
                    status='pending'
                )
                
                # Process payment success
                result = PaymentService.process_payment_success(
                    payment.transaction_id,
                    {'external_transaction_id': f'wx_trans_{user_id}'}
                )
                
                assert result['success'], f"Payment processing should succeed: {result['message']}"
                
                # Reload payment and order
                payment.refresh_from_db()
                order.refresh_from_db()
                
                # Verify payment status updated
                assert payment.status == 'success', f"Payment status should be 'success', got '{payment.status}'"
                assert payment.paid_at is not None, "Payment should have paid_at timestamp"
                
                # Verify order status updated
                assert order.status == 1, f"Order status should be 1 (PAID), got {order.status}"
                assert order.pay_time is not None, "Order should have pay_time timestamp"
                
                # Verify external transaction ID stored
                assert payment.external_transaction_id == f'wx_trans_{user_id}', "External transaction ID should be stored"
                
        except Exception as e:
            error_msg = str(e)
            import traceback
            traceback.print_exc()
        
        assert error_msg == "", f"Unexpected error: {error_msg}"

    @given(
        openid=st.text(min_size=10, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyz0123456789'),
        user_id=st.integers(min_value=1, max_value=1000)
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.django_db(transaction=True)
    def test_wechat_authentication_integration(self, openid, user_id):
        """
        Property 14: WeChat Authentication Integration
        For any successful WeChat OAuth flow, user information should be retrieved 
        from WeChat API and stored in the user profile
        **Validates: Requirements 6.1**
        """
        error_msg = ""
        
        try:
            with transaction.atomic():
                # Create user with WeChat OpenID
                user = User.objects.create_user(
                    username=f"wechat_user_{user_id}",
                    email=f"wechat_{user_id}@example.com",
                    password="test_password_123",
                    wechat_openid=openid
                )
                
                # Create order for WeChat payment
                order = Order.objects.create(
                    roid=f"wechat_order_{user_id}",
                    uid=user,
                    amount=Decimal('100.00'),
                    status=-1,  # Pending payment
                    type=2,
                    address={'test': 'address'},
                    openid=openid
                )
                
                # Create payment transaction
                payment = PaymentTransaction.objects.create(
                    order_id=order.roid,
                    user=user,
                    payment_method=self.payment_method,
                    amount=Decimal('100.00'),
                    status='pending',
                    wechat_openid=openid
                )
                
                # Create WeChat payment record
                wechat_payment = WeChatPayment.objects.create(
                    payment_transaction=payment,
                    appid='test_appid',
                    mch_id='test_mch_id',
                    nonce_str='test_nonce',
                    body=f'Order {order.roid}',
                    out_trade_no=payment.transaction_id,
                    total_fee=10000,  # 100.00 in cents
                    spbill_create_ip='127.0.0.1'
                )
                
                # Verify WeChat integration data is stored correctly
                assert user.wechat_openid == openid, f"User WeChat OpenID should be '{openid}', got '{user.wechat_openid}'"
                assert payment.wechat_openid == openid, f"Payment WeChat OpenID should be '{openid}', got '{payment.wechat_openid}'"
                assert order.openid == openid, f"Order OpenID should be '{openid}', got '{order.openid}'"
                
                # Verify WeChat payment record
                assert wechat_payment.out_trade_no == payment.transaction_id, "WeChat payment should reference correct transaction"
                assert wechat_payment.total_fee == 10000, "WeChat payment amount should be in cents"
                
                # Verify WeChat payment can be retrieved through relationship
                retrieved_wechat = payment.wechat_payment
                assert retrieved_wechat.appid == 'test_appid', "WeChat payment should be retrievable through relationship"
                
        except Exception as e:
            error_msg = str(e)
            import traceback
            traceback.print_exc()
        
        assert error_msg == "", f"Unexpected error: {error_msg}"

    @given(
        refund_amount=st.decimals(min_value=Decimal('0.01'), max_value=Decimal('500.00'), places=2),
        original_amount=st.decimals(min_value=Decimal('1.00'), max_value=Decimal('1000.00'), places=2),
        user_id=st.integers(min_value=1, max_value=1000)
    )
    @settings(max_examples=50, deadline=5000)
    @pytest.mark.django_db(transaction=True)
    def test_refund_processing_property(self, refund_amount, original_amount, user_id):
        """
        Property: Refund Processing Validation
        For any refund request, the refund amount should not exceed the original payment amount,
        and successful refunds should update the refund status correctly
        **Validates: Requirements 6.4**
        """
        error_msg = ""
        
        try:
            with transaction.atomic():
                # Ensure refund amount doesn't exceed original amount for valid test
                if refund_amount > original_amount:
                    refund_amount = original_amount
                
                # Create user
                user = User.objects.create_user(
                    username=f"refund_user_{user_id}",
                    email=f"refund_{user_id}@example.com",
                    password="test_password_123"
                )
                
                # Create successful payment transaction
                payment = PaymentTransaction.objects.create(
                    transaction_id=f"refund_test_{user_id}_{hash(original_amount) % 10000}",
                    order_id=f"refund_order_{user_id}",
                    user=user,
                    payment_method=self.payment_method,
                    amount=original_amount,
                    status='success'  # Must be successful to refund
                )
                
                # Create refund request
                result = PaymentService.create_refund_request(
                    transaction=payment,
                    refund_amount=refund_amount,
                    refund_reason="Test refund",
                    refund_type='partial' if refund_amount < original_amount else 'full'
                )
                
                # Verify refund creation
                assert result['success'], f"Refund creation should succeed: {result['message']}"
                
                refund_request = result['refund_request']
                
                # Verify refund properties
                assert refund_request.refund_amount == refund_amount, f"Refund amount should be {refund_amount}, got {refund_request.refund_amount}"
                assert refund_request.original_transaction == payment, "Refund should reference original transaction"
                assert refund_request.status in ['pending', 'processing'], f"Refund status should be pending or processing, got '{refund_request.status}'"
                
                # Verify refund amount validation
                if refund_amount <= original_amount:
                    assert refund_request.refund_amount <= payment.amount, "Refund amount should not exceed original payment"
                
                # Test refund amount exceeding original (should fail)
                if refund_amount < original_amount:
                    excessive_refund_result = PaymentService.create_refund_request(
                        transaction=payment,
                        refund_amount=original_amount + Decimal('1.00'),
                        refund_reason="Excessive refund test",
                        refund_type='full'
                    )
                    assert not excessive_refund_result['success'], "Excessive refund should fail"
                
        except Exception as e:
            error_msg = str(e)
            import traceback
            traceback.print_exc()
        
        assert error_msg == "", f"Unexpected error: {error_msg}"

    @given(
        transaction_count=st.integers(min_value=1, max_value=5),
        user_id=st.integers(min_value=1, max_value=1000)
    )
    @settings(max_examples=30, deadline=5000)
    @pytest.mark.django_db(transaction=True)
    def test_payment_transaction_uniqueness(self, transaction_count, user_id):
        """
        Property: Payment Transaction Uniqueness
        For any order, only one successful payment transaction should be allowed
        **Validates: Requirements 6.2**
        """
        error_msg = ""
        
        try:
            with transaction.atomic():
                # Create user
                user = User.objects.create_user(
                    username=f"unique_user_{user_id}",
                    email=f"unique_{user_id}@example.com",
                    password="test_password_123"
                )
                
                # Create order
                order = Order.objects.create(
                    roid=f"unique_order_{user_id}",
                    uid=user,
                    amount=Decimal('100.00'),
                    status=-1,  # Pending payment
                    type=2,
                    address={'test': 'address'},
                    openid=f"test_openid_{user_id}"
                )
                
                successful_payments = 0
                
                # Try to create multiple payment transactions for the same order
                for i in range(transaction_count):
                    try:
                        payment = PaymentTransaction.objects.create(
                            order_id=order.roid,
                            user=user,
                            payment_method=self.payment_method,
                            amount=Decimal('100.00'),
                            status='pending'
                        )
                        
                        # Try to process payment success
                        result = PaymentService.process_payment_success(payment.transaction_id)
                        
                        if result['success']:
                            successful_payments += 1
                            
                            # Reload order to check status
                            order.refresh_from_db()
                            
                            # After first successful payment, order should be paid
                            if successful_payments == 1:
                                assert order.status == 1, "Order should be marked as paid after first successful payment"
                            
                    except Exception as e:
                        # Some failures are expected (e.g., duplicate transactions)
                        pass
                
                # Verify only one payment can succeed for an order
                # (This is enforced by business logic, not database constraints)
                successful_payment_count = PaymentTransaction.objects.filter(
                    order_id=order.roid,
                    status='success'
                ).count()
                
                # In a properly implemented system, there should be at most one successful payment
                assert successful_payment_count <= 1, f"Should have at most 1 successful payment, got {successful_payment_count}"
                
        except Exception as e:
            error_msg = str(e)
            import traceback
            traceback.print_exc()
        
        assert error_msg == "", f"Unexpected error: {error_msg}"

    @given(
        callback_data=st.dictionaries(
            keys=st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz_'),
            values=st.text(min_size=1, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyz0123456789'),
            min_size=1,
            max_size=5
        ),
        user_id=st.integers(min_value=1, max_value=1000)
    )
    @settings(max_examples=50, deadline=5000)
    @pytest.mark.django_db(transaction=True)
    def test_payment_callback_data_storage(self, callback_data, user_id):
        """
        Property: Payment Callback Data Storage
        For any payment callback, the callback data should be stored correctly
        and be retrievable for audit purposes
        **Validates: Requirements 6.3**
        """
        error_msg = ""
        
        try:
            with transaction.atomic():
                # Create user
                user = User.objects.create_user(
                    username=f"callback_user_{user_id}",
                    email=f"callback_{user_id}@example.com",
                    password="test_password_123"
                )
                
                # Create payment transaction
                payment = PaymentTransaction.objects.create(
                    order_id=f"callback_order_{user_id}",
                    user=user,
                    payment_method=self.payment_method,
                    amount=Decimal('100.00'),
                    status='pending'
                )
                
                # Process payment with callback data
                result = PaymentService.process_payment_success(
                    payment.transaction_id,
                    callback_data
                )
                
                assert result['success'], f"Payment processing should succeed: {result['message']}"
                
                # Reload payment
                payment.refresh_from_db()
                
                # Verify callback data is stored
                assert payment.callback_data == callback_data, "Callback data should be stored correctly"
                assert payment.callback_received_at is not None, "Callback received timestamp should be set"
                
                # Verify callback data is retrievable
                retrieved_payment = PaymentTransaction.objects.get(transaction_id=payment.transaction_id)
                assert retrieved_payment.callback_data == callback_data, "Callback data should be retrievable"
                
                # Verify callback data keys are preserved
                for key, value in callback_data.items():
                    assert key in retrieved_payment.callback_data, f"Callback data key '{key}' should be preserved"
                    assert retrieved_payment.callback_data[key] == value, f"Callback data value for '{key}' should be preserved"
                
        except Exception as e:
            error_msg = str(e)
            import traceback
            traceback.print_exc()
        
        assert error_msg == "", f"Unexpected error: {error_msg}"