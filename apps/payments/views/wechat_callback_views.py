"""
WeChat Pay callback views.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
import logging

from ..models import PaymentCallback
from ..services import WeChatPayService

logger = logging.getLogger(__name__)


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

