from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from decimal import Decimal
import logging

from .models import PaymentMethod, PaymentTransaction, RefundRequest, WeChatPayment, PaymentCallback
from .serializers import (
    PaymentMethodSerializer,
    PaymentTransactionListSerializer, PaymentTransactionSerializer,
    PaymentCreateSerializer,
    RefundRequestListSerializer, RefundRequestSerializer,
    RefundCreateSerializer, PaymentStatusSerializer,
    PaymentCallbackSerializer
)
from .services import PaymentService, WeChatPayService
from apps.orders.models import Order
from apps.common.utils import success_response, error_response

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_payment_methods(request):
    """Get available payment methods"""
    try:
        methods = PaymentMethod.objects.filter(is_active=True)
        serializer = PaymentMethodSerializer(methods, many=True)
        
        return success_response(
            data=serializer.data,
            message="Payment methods retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to get payment methods: {e}")
        return error_response("Failed to retrieve payment methods")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment(request):
    """Create payment transaction for an order"""
    try:
        serializer = PaymentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid payment data", serializer.errors)
        
        data = serializer.validated_data
        
        # Get order with related objects to avoid N+1 queries
        try:
            order = Order.objects.select_related('uid').prefetch_related('items', 'discounts').get(
                roid=data['order_id'], uid=request.user
            )
        except Order.DoesNotExist:
            return error_response("Order not found")
        
        # Check order status
        if order.status != -1:  # Not pending payment
            return error_response("Order is not in pending payment status")
        
        # Check if payment already exists (with select_related for payment_method)
        existing_payment = PaymentTransaction.objects.select_related('payment_method').filter(
            order_id=data['order_id'],
            status__in=['pending', 'processing', 'success']
        ).first()
        
        if existing_payment:
            if existing_payment.status == 'success':
                return error_response("Order has already been paid")
            elif existing_payment.status in ['pending', 'processing']:
                # Return existing payment info
                serializer = PaymentTransactionSerializer(existing_payment)
                return success_response(
                    data=serializer.data,
                    message="Payment transaction already exists"
                )
        
        # Create payment transaction
        payment_result = PaymentService.create_payment(
            user=request.user,
            order=order,
            payment_method=data['payment_method'],
            return_url=data.get('return_url'),
            notify_url=data.get('notify_url')
        )
        
        if not payment_result['success']:
            return error_response(payment_result['message'])
        
        payment_transaction = payment_result['payment_transaction']
        serializer = PaymentTransactionSerializer(payment_transaction)
        
        response_data = serializer.data
        
        # Add payment method specific data
        if payment_result.get('payment_data'):
            response_data.update(payment_result['payment_data'])
        
        return success_response(
            data=response_data,
            message="Payment transaction created successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to create payment: {e}")
        return error_response("Failed to create payment transaction")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_payment_status(request, transaction_id):
    """Get payment transaction status"""
    try:
        # Use select_related to avoid N+1 queries
        payment = get_object_or_404(
            PaymentTransaction.objects.select_related('payment_method', 'user'),
            transaction_id=transaction_id,
            user=request.user
        )
        
        serializer = PaymentStatusSerializer({
            'transaction_id': payment.transaction_id,
            'order_id': payment.order_id,
            'status': payment.status,
            'amount': payment.amount,
            'paid_at': payment.paid_at,
            'error_message': payment.error_message,
            'wechat_transaction_id': getattr(payment, 'wechat_payment', {}).get('transaction_id', ''),
            'wechat_prepay_id': payment.wechat_prepay_id
        })
        
        return success_response(
            data=serializer.data,
            message="Payment status retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to get payment status: {e}")
        return error_response("Failed to retrieve payment status")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_payment(request, transaction_id):
    """Cancel a pending payment transaction"""
    try:
        # Use select_related to avoid N+1 queries
        payment = get_object_or_404(
            PaymentTransaction.objects.select_related('payment_method', 'user'),
            transaction_id=transaction_id,
            user=request.user
        )
        
        if payment.status not in ['pending', 'processing']:
            return error_response("Payment cannot be cancelled in current status")
        
        # Cancel payment
        result = PaymentService.cancel_payment(payment)
        
        if not result['success']:
            return error_response(result['message'])
        
        return success_response(message="Payment cancelled successfully")
        
    except Exception as e:
        logger.error(f"Failed to cancel payment: {e}")
        return error_response("Failed to cancel payment")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_refund(request):
    """Create refund request"""
    try:
        serializer = RefundCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid refund data", serializer.errors)
        
        data = serializer.validated_data
        
        # Get original transaction with related objects
        try:
            transaction = PaymentTransaction.objects.select_related('payment_method', 'user').get(
                transaction_id=data['transaction_id'],
                user=request.user,
                status='success'
            )
        except PaymentTransaction.DoesNotExist:
            return error_response("Transaction not found or not eligible for refund")
        
        # Check refund amount
        if data['refund_amount'] > transaction.amount:
            return error_response("Refund amount cannot exceed original payment amount")
        
        # Create refund request
        result = PaymentService.create_refund_request(
            transaction=transaction,
            refund_amount=data['refund_amount'],
            refund_reason=data['refund_reason'],
            refund_type=data['refund_type'],
            return_order_id=data.get('return_order_id')
        )
        
        if not result['success']:
            return error_response(result['message'])
        
        refund_request = result['refund_request']
        serializer = RefundRequestSerializer(refund_request)
        
        return success_response(
            data=serializer.data,
            message="Refund request created successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to create refund: {e}")
        return error_response("Failed to create refund request")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_payments(request):
    """Get user's payment transactions"""
    try:
        # Use select_related to avoid N+1 queries for payment_method
        payments = PaymentTransaction.objects.select_related('payment_method').filter(
            user=request.user
        ).order_by('-created_at')
        
        # Apply filters
        status_filter = request.GET.get('status')
        if status_filter:
            payments = payments.filter(status=status_filter)
        
        order_id_filter = request.GET.get('order_id')
        if order_id_filter:
            payments = payments.filter(order_id=order_id_filter)
        
        # Pagination
        page_size = int(request.GET.get('pageSize', 10))
        page_index = int(request.GET.get('pageIndex', 0))
        
        start = page_index * page_size
        end = start + page_size
        
        paginated_payments = payments[start:end]
        # Use list serializer for list view
        serializer = PaymentTransactionListSerializer(paginated_payments, many=True)
        
        return success_response(
            data={
                'payments': serializer.data,
                'total': payments.count(),
                'pageIndex': page_index,
                'pageSize': page_size
            },
            message="Payment transactions retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to get user payments: {e}")
        return error_response("Failed to retrieve payment transactions")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_refunds(request):
    """Get user's refund requests"""
    try:
        refunds = RefundRequest.objects.filter(
            original_transaction__user=request.user
        ).select_related('original_transaction').order_by('-requested_at')
        
        # Apply filters
        status_filter = request.GET.get('status')
        if status_filter:
            refunds = refunds.filter(status=status_filter)
        
        order_id_filter = request.GET.get('order_id')
        if order_id_filter:
            refunds = refunds.filter(order_id=order_id_filter)
        
        # Pagination
        page_size = int(request.GET.get('pageSize', 10))
        page_index = int(request.GET.get('pageIndex', 0))
        
        start = page_index * page_size
        end = start + page_size
        
        paginated_refunds = refunds[start:end]
        # Use list serializer for list view
        serializer = RefundRequestListSerializer(paginated_refunds, many=True)
        
        return success_response(
            data={
                'refunds': serializer.data,
                'total': refunds.count(),
                'pageIndex': page_index,
                'pageSize': page_size
            },
            message="Refund requests retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to get user refunds: {e}")
        return error_response("Failed to retrieve refund requests")


# WeChat Pay specific endpoints

@api_view(['POST'])
@permission_classes([AllowAny])
def wechat_pay_callback(request):
    """WeChat Pay payment callback endpoint"""
    try:
        # Log callback for debugging
        callback_log = PaymentCallback.objects.create(
            callback_type='payment',
            payment_method='wechat_pay',
            request_method=request.method,
            request_path=request.path,
            request_headers=dict(request.headers),
            request_body=request.body.decode('utf-8') if request.body else '',
            request_ip=request.META.get('REMOTE_ADDR', ''),
            response_status=200,
            response_body='',
        )
        
        # Process WeChat Pay callback
        result = WeChatPayService.process_payment_callback(request.body)
        
        if result['success']:
            callback_log.processed = True
            callback_log.transaction_id = result.get('transaction_id', '')
            callback_log.response_body = result['response']
        else:
            callback_log.processed = False
            callback_log.processing_error = result['message']
            callback_log.response_body = result['response']
            callback_log.response_status = 400
        
        callback_log.save()
        
        # Return WeChat Pay expected response format
        from django.http import HttpResponse
        return HttpResponse(
            result['response'],
            content_type='application/xml',
            status=200 if result['success'] else 400
        )
        
    except Exception as e:
        logger.error(f"WeChat Pay callback error: {e}")
        
        # Update callback log with error
        if 'callback_log' in locals():
            callback_log.processed = False
            callback_log.processing_error = str(e)
            callback_log.response_status = 500
            callback_log.save()
        
        # Return WeChat Pay error response
        from django.http import HttpResponse
        return HttpResponse(
            '<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[System Error]]></return_msg></xml>',
            content_type='application/xml',
            status=500
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def wechat_refund_callback(request):
    """WeChat Pay refund callback endpoint"""
    try:
        # Log callback for debugging
        callback_log = PaymentCallback.objects.create(
            callback_type='refund',
            payment_method='wechat_pay',
            request_method=request.method,
            request_path=request.path,
            request_headers=dict(request.headers),
            request_body=request.body.decode('utf-8') if request.body else '',
            request_ip=request.META.get('REMOTE_ADDR', ''),
            response_status=200,
            response_body='',
        )
        
        # Process WeChat Pay refund callback
        result = WeChatPayService.process_refund_callback(request.body)
        
        if result['success']:
            callback_log.processed = True
            callback_log.refund_id = result.get('refund_id', '')
            callback_log.response_body = result['response']
        else:
            callback_log.processed = False
            callback_log.processing_error = result['message']
            callback_log.response_body = result['response']
            callback_log.response_status = 400
        
        callback_log.save()
        
        # Return WeChat Pay expected response format
        from django.http import HttpResponse
        return HttpResponse(
            result['response'],
            content_type='application/xml',
            status=200 if result['success'] else 400
        )
        
    except Exception as e:
        logger.error(f"WeChat Pay refund callback error: {e}")
        
        # Update callback log with error
        if 'callback_log' in locals():
            callback_log.processed = False
            callback_log.processing_error = str(e)
            callback_log.response_status = 500
            callback_log.save()
        
        # Return WeChat Pay error response
        from django.http import HttpResponse
        return HttpResponse(
            '<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[System Error]]></return_msg></xml>',
            content_type='application/xml',
            status=500
        )