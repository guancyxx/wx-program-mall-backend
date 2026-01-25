"""
Refund request serializers for list, detail, and create operations.
"""
from rest_framework import serializers
from ..models import RefundRequest, PaymentTransaction
from apps.common.validators import validate_price_range


class RefundRequestListSerializer(serializers.ModelSerializer):
    """
    Serializer for refund request list view - minimal fields for list display.
    Used for: GET /api/payments/refunds/
    """
    original_transaction_id = serializers.CharField(source='original_transaction.transaction_id', read_only=True)
    
    class Meta:
        model = RefundRequest
        fields = [
            'refund_id', 'original_transaction_id', 'order_id', 'return_order_id',
            'refund_type', 'refund_amount', 'status', 'requested_at'
        ]
        read_only_fields = [
            'refund_id', 'status', 'requested_at'
        ]


class RefundRequestSerializer(serializers.ModelSerializer):
    """
    Serializer for refund request detail view - complete fields for detail display.
    Used for: GET /api/payments/refunds/{id}/
    Note: admin_notes field is read-only and should only be visible to admins.
    """
    original_transaction_id = serializers.CharField(source='original_transaction.transaction_id', read_only=True)
    
    class Meta:
        model = RefundRequest
        fields = [
            'refund_id', 'original_transaction_id', 'order_id', 'return_order_id',
            'refund_type', 'refund_amount', 'refund_reason', 'status',
            'external_refund_id', 'requested_at', 'processed_at', 'completed_at',
            'error_code', 'error_message', 'admin_notes'
        ]
        read_only_fields = [
            'refund_id', 'external_refund_id', 'status',
            'requested_at', 'processed_at', 'completed_at',
            'error_code', 'error_message', 'admin_notes'
        ]


class RefundCreateSerializer(serializers.Serializer):
    """
    Serializer for creating refund requests.
    Used for: POST /api/payments/refunds/create/
    """
    transaction_id = serializers.CharField(max_length=100, help_text="Original transaction ID")
    refund_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Refund amount"
    )
    refund_reason = serializers.CharField(max_length=500, help_text="Reason for refund")
    refund_type = serializers.ChoiceField(
        choices=RefundRequest.REFUND_TYPE_CHOICES,
        default='full',
        help_text="Type of refund"
    )
    return_order_id = serializers.CharField(
        max_length=50, 
        required=False,
        allow_blank=True,
        help_text="Return order ID if applicable"
    )
    
    def validate_transaction_id(self, value):
        """Validate transaction exists and can be refunded"""
        try:
            transaction = PaymentTransaction.objects.get(transaction_id=value, status='success')
            return value
        except PaymentTransaction.DoesNotExist:
            raise serializers.ValidationError("Transaction not found or not eligible for refund")
    
    def validate_refund_amount(self, value):
        """Validate refund amount is positive"""
        return validate_price_range(value, min_value=0)








