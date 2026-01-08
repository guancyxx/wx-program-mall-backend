"""
Payment method views.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import logging

from apps.common.utils import success_response, error_response
from ..models import PaymentMethod
from ..serializers import PaymentMethodSerializer

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

