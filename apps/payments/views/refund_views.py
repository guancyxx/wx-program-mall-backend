"""
Refund request views.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import logging

from apps.common.utils import success_response, error_response
from ..models import PaymentTransaction, RefundRequest
from ..serializers import (
    RefundRequestListSerializer, RefundRequestSerializer,
    RefundCreateSerializer
)
from ..services import PaymentService

logger = logging.getLogger(__name__)


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

