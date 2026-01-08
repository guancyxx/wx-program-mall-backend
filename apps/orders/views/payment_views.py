"""
Payment status and callback views.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.common.utils import success_response, error_response
from ..models import Order


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pay_status(request):
    """Check payment status endpoint matching Node.js /api/order/getPayStatus"""
    try:
        roid = request.GET.get('roid')
        if not roid:
            return error_response("Order ID (roid) is required")

        try:
            order = Order.objects.get(roid=roid, uid=request.user)
        except Order.DoesNotExist:
            return error_response("Order not found")

        if order.status == 1:  # Paid
            # TODO: Generate QR code for pickup orders if needed
            if order.type == 1 and not order.qrcode:
                # Generate QR code logic would go here
                pass
            
            return success_response({
                'amount': float(order.amount)
            }, 'Order payment successful')
        else:
            return error_response("Order not paid")

    except Exception as e:
        return error_response(f"Server error: {str(e)}")


@api_view(['POST'])
@permission_classes([])  # No authentication for callback
def payment_callback(request):
    """WeChat Pay callback endpoint matching Node.js /api/order/callback"""
    try:
        # Import payment service
        from apps.payments.services import WeChatPayService
        
        # Process WeChat Pay callback using the new payment system
        result = WeChatPayService.process_payment_callback(request.body)
        
        if result['success']:
            # Return WeChat Pay expected XML response
            from django.http import HttpResponse
            return HttpResponse(
                result['response'],
                content_type='application/xml',
                status=200
            )
        else:
            # Return WeChat Pay error response
            from django.http import HttpResponse
            return HttpResponse(
                result['response'],
                content_type='application/xml',
                status=400
            )

    except Exception as e:
        # Return WeChat Pay error response for any system errors
        from django.http import HttpResponse
        return HttpResponse(
            '<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[System Error]]></return_msg></xml>',
            content_type='application/xml',
            status=500
        )

