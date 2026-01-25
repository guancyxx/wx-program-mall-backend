"""
QR code generation views for order verification.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from apps.common.utils import error_response
from ..models import Order
from ..services.order_payment_service import OrderPaymentService


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_order_qr_code(request, roid):
    """
    Generate QR code for order verification
    GET /api/order/qr/{roid}/
    """
    try:
        # Get order
        order = get_object_or_404(Order, roid=roid)
        
        # Only allow order owner or admin to view QR code
        if order.uid != request.user and not request.user.is_staff:
            return error_response("Permission denied")
        
        # Only pickup orders have QR codes
        if order.type != 1:
            return error_response("Only pickup orders have QR codes")
        
        # Generate QR code
        qr_code_url = OrderPaymentService.generate_order_qr_code(order)
        
        # If QR code is a data URL, extract the base64 part and return as image
        if qr_code_url.startswith('data:image/png;base64,'):
            import base64
            from io import BytesIO
            
            # Extract base64 data
            base64_data = qr_code_url.split(',')[1]
            image_data = base64.b64decode(base64_data)
            
            # Return as PNG image
            response = HttpResponse(image_data, content_type='image/png')
            response['Cache-Control'] = 'public, max-age=3600'
            return response
        else:
            # If it's a URL, redirect to it (fallback case)
            from django.shortcuts import redirect
            return redirect(qr_code_url)
            
    except Order.DoesNotExist:
        return error_response("Order not found")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to generate QR code for order {roid}: {e}")
        return error_response(f"Failed to generate QR code: {str(e)}")

