"""
Payment service for payment operations.
"""
from django.db import transaction
from django.utils import timezone
from typing import Dict
import logging

from ..models import PaymentMethod, PaymentTransaction, RefundRequest
from apps.orders.models import Order
from apps.orders.services import OrderPaymentService

logger = logging.getLogger(__name__)


class PaymentService:
    """Service class for payment operations"""

    @staticmethod
    @transaction.atomic
    def create_payment(user, order: Order, payment_method: str, return_url: str = None, notify_url: str = None) -> Dict:
        """Create payment transaction"""
        try:
            # Get payment method
            try:
                method = PaymentMethod.objects.get(name=payment_method, is_active=True)
            except PaymentMethod.DoesNotExist:
                return {'success': False, 'message': 'Invalid payment method'}
            
            # Create payment transaction
            payment_transaction = PaymentTransaction.objects.create(
                order_id=order.roid,
                user=user,
                payment_method=method,
                amount=order.amount,
                wechat_openid=getattr(user, 'wechat_openid', ''),
                payment_data={
                    'return_url': return_url,
                    'notify_url': notify_url,
                    'order_type': order.type,
                    'order_address': order.address
                }
            )
            
            # Process payment based on method
            if payment_method == 'wechat_pay':
                from .wechat_pay_service import WeChatPayService
                # Get client IP from request if available (for V2 API compatibility)
                # Note: V3 API doesn't require client IP, but we store it for compatibility
                result = WeChatPayService.create_payment(
                    payment_transaction, 
                    order, 
                    notify_url=notify_url,
                    client_ip=None  # V3 API doesn't require this, but we'll use default
                )
                if not result['success']:
                    payment_transaction.status = 'failed'
                    payment_transaction.error_message = result['message']
                    payment_transaction.save()
                    return result
                
                # Update payment with WeChat Pay data
                payment_transaction.wechat_prepay_id = result.get('prepay_id', '')
                payment_transaction.external_transaction_id = result.get('prepay_id', '')
                payment_transaction.save()
                
                return {
                    'success': True,
                    'message': 'Payment created successfully',
                    'payment_transaction': payment_transaction,
                    'payment_data': result.get('payment_data', {})
                }
            
            else:
                return {'success': False, 'message': 'Payment method not implemented'}
            
        except Exception as e:
            logger.error(f"Failed to create payment: {e}")
            return {'success': False, 'message': f'Failed to create payment: {str(e)}'}

    @staticmethod
    @transaction.atomic
    def process_payment_success(transaction_id: str, external_data: Dict = None) -> Dict:
        """Process successful payment"""
        try:
            payment = PaymentTransaction.objects.get(transaction_id=transaction_id)
            
            if payment.status != 'pending':
                return {'success': False, 'message': 'Payment is not in pending status'}
            
            # Update payment status
            payment.status = 'success'
            payment.paid_at = timezone.now()
            
            if external_data:
                payment.external_transaction_id = external_data.get('external_transaction_id', payment.external_transaction_id)
                payment.callback_data = external_data
                payment.callback_received_at = timezone.now()
            
            payment.save()
            
            # Update order status using order_id (roid)
            success, message = OrderPaymentService.process_payment_success(payment.order_id)
            if not success:
                logger.error(f"Failed to update order status for payment {transaction_id} (order: {payment.order_id}): {message}")
                # Don't fail the payment processing, just log the error
            
            return {'success': True, 'message': 'Payment processed successfully'}
            
        except PaymentTransaction.DoesNotExist:
            return {'success': False, 'message': 'Payment transaction not found'}
        except Exception as e:
            logger.error(f"Failed to process payment success: {e}")
            return {'success': False, 'message': f'Failed to process payment: {str(e)}'}

    @staticmethod
    @transaction.atomic
    def cancel_payment(payment: PaymentTransaction) -> Dict:
        """Cancel payment transaction"""
        try:
            if payment.status not in ['pending', 'processing']:
                return {'success': False, 'message': 'Payment cannot be cancelled in current status'}
            
            payment.status = 'cancelled'
            payment.save()
            
            return {'success': True, 'message': 'Payment cancelled successfully'}
            
        except Exception as e:
            logger.error(f"Failed to cancel payment: {e}")
            return {'success': False, 'message': f'Failed to cancel payment: {str(e)}'}

    @staticmethod
    @transaction.atomic
    def create_refund_request(transaction: PaymentTransaction, refund_amount, 
                            refund_reason: str, refund_type: str = 'full', 
                            return_order_id: str = None) -> Dict:
        """Create refund request"""
        try:
            # Check if refund amount is valid
            if refund_amount > transaction.amount:
                return {'success': False, 'message': 'Refund amount exceeds original payment amount'}
            
            # Check for existing refunds
            existing_refunds = RefundRequest.objects.filter(
                original_transaction=transaction,
                status__in=['pending', 'processing', 'success']
            )
            
            total_refunded = sum(refund.refund_amount for refund in existing_refunds)
            if total_refunded + refund_amount > transaction.amount:
                return {'success': False, 'message': 'Total refund amount exceeds original payment amount'}
            
            # Create refund request
            refund_request = RefundRequest.objects.create(
                original_transaction=transaction,
                order_id=transaction.order_id,
                return_order_id=return_order_id,
                refund_type=refund_type,
                refund_amount=refund_amount,
                refund_reason=refund_reason
            )
            
            # Process refund based on payment method
            if transaction.payment_method.name == 'wechat_pay':
                from .wechat_pay_service import WeChatPayService
                result = WeChatPayService.create_refund(refund_request)
                if not result['success']:
                    refund_request.status = 'failed'
                    refund_request.error_message = result['message']
                    refund_request.save()
                    return result
                
                refund_request.external_refund_id = result.get('refund_id', '')
                refund_request.status = 'processing'
                refund_request.save()
            
            return {
                'success': True,
                'message': 'Refund request created successfully',
                'refund_request': refund_request
            }
            
        except Exception as e:
            logger.error(f"Failed to create refund request: {e}")
            return {'success': False, 'message': f'Failed to create refund request: {str(e)}'}


