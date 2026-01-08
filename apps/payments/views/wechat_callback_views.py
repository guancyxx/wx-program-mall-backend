"""
WeChat Pay V3 callback views.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
import json
import logging

from ..models import PaymentCallback
from ..services import WeChatPayService

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def wechat_pay_callback(request):
    """WeChat Pay V3 payment callback endpoint"""
    try:
        # Log callback for debugging
        request_body_str = request.body.decode('utf-8') if request.body else ''
        callback_log = PaymentCallback.objects.create(
            callback_type='payment',
            payment_method='wechat_pay',
            request_method=request.method,
            request_path=request.path,
            request_headers=dict(request.headers),
            request_body=request_body_str,
            request_ip=request.META.get('REMOTE_ADDR', ''),
            response_status=200,
            response_body='',
        )
        
        # Process WeChat Pay V3 callback (JSON format)
        result = WeChatPayService.process_payment_callback(
            request.body,
            headers=dict(request.headers)
        )
        
        # Prepare response (V3 API uses JSON)
        if result['success']:
            callback_log.processed = True
            callback_log.transaction_id = result.get('transaction_id', '')
            response_data = result.get('response', {'code': 'SUCCESS', 'message': 'OK'})
        else:
            callback_log.processed = False
            callback_log.processing_error = result['message']
            response_data = result.get('response', {'code': 'FAIL', 'message': result['message']})
            callback_log.response_status = 400
        
        callback_log.response_body = json.dumps(response_data, ensure_ascii=False)
        callback_log.save()
        
        # Return JSON response for V3 API
        return Response(
            response_data,
            status=200 if result['success'] else 400
        )
        
    except Exception as e:
        logger.error(f"WeChat Pay callback error: {e}", exc_info=True)
        
        # Update callback log with error
        if 'callback_log' in locals():
            callback_log.processed = False
            callback_log.processing_error = str(e)
            callback_log.response_status = 500
            callback_log.response_body = json.dumps({'code': 'FAIL', 'message': 'System error'}, ensure_ascii=False)
            callback_log.save()
        
        # Return JSON error response for V3 API
        return Response(
            {'code': 'FAIL', 'message': 'System error'},
            status=500
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def wechat_refund_callback(request):
    """WeChat Pay V3 refund callback endpoint"""
    try:
        # Log callback for debugging
        request_body_str = request.body.decode('utf-8') if request.body else ''
        callback_log = PaymentCallback.objects.create(
            callback_type='refund',
            payment_method='wechat_pay',
            request_method=request.method,
            request_path=request.path,
            request_headers=dict(request.headers),
            request_body=request_body_str,
            request_ip=request.META.get('REMOTE_ADDR', ''),
            response_status=200,
            response_body='',
        )
        
        # Process WeChat Pay V3 refund callback (JSON format)
        result = WeChatPayService.process_refund_callback(
            request.body,
            headers=dict(request.headers)
        )
        
        # Prepare response (V3 API uses JSON)
        if result['success']:
            callback_log.processed = True
            callback_log.refund_id = result.get('refund_id', '')
            response_data = result.get('response', {'code': 'SUCCESS', 'message': 'OK'})
        else:
            callback_log.processed = False
            callback_log.processing_error = result['message']
            response_data = result.get('response', {'code': 'FAIL', 'message': result['message']})
            callback_log.response_status = 400
        
        callback_log.response_body = json.dumps(response_data, ensure_ascii=False)
        callback_log.save()
        
        # Return JSON response for V3 API
        return Response(
            response_data,
            status=200 if result['success'] else 400
        )
        
    except Exception as e:
        logger.error(f"WeChat Pay refund callback error: {e}", exc_info=True)
        
        # Update callback log with error
        if 'callback_log' in locals():
            callback_log.processed = False
            callback_log.processing_error = str(e)
            callback_log.response_status = 500
            callback_log.response_body = json.dumps({'code': 'FAIL', 'message': 'System error'}, ensure_ascii=False)
            callback_log.save()
        
        # Return JSON error response for V3 API
        return Response(
            {'code': 'FAIL', 'message': 'System error'},
            status=500
        )

