"""
Payment transaction serializers for list, detail, create, and status operations.
"""
from rest_framework import serializers
from ..models import PaymentTransaction, PaymentMethod


class PaymentTransactionListSerializer(serializers.ModelSerializer):
    """
    Serializer for payment transaction list view - minimal fields for list display.
    Used for: GET /api/payments/transactions/
    """
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    payment_method_display = serializers.CharField(source='payment_method.display_name', read_only=True)
    
    class Meta:
        model = PaymentTransaction
        fields = [
            'transaction_id', 'order_id', 'payment_method_name', 'payment_method_display',
            'amount', 'currency', 'status', 'created_at', 'paid_at'
        ]
        read_only_fields = [
            'transaction_id', 'created_at', 'paid_at'
        ]


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for payment transaction detail view - complete fields for detail display.
    Used for: GET /api/payments/transactions/{id}/
    Note: Sensitive fields like wechat_openid are included but should be protected by permissions.
    """
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    payment_method_display = serializers.CharField(source='payment_method.display_name', read_only=True)
    
    class Meta:
        model = PaymentTransaction
        fields = [
            'transaction_id', 'order_id', 'payment_method_name', 'payment_method_display',
            'amount', 'currency', 'status', 'external_transaction_id', 'external_order_id',
            'wechat_openid', 'wechat_prepay_id', 'created_at', 'paid_at', 'expired_at',
            'error_code', 'error_message'
        ]
        read_only_fields = [
            'transaction_id', 'external_transaction_id', 'external_order_id',
            'wechat_prepay_id', 'created_at', 'paid_at', 'expired_at',
            'error_code', 'error_message'
        ]


class PaymentCreateSerializer(serializers.Serializer):
    """
    Serializer for creating payment transactions.
    Used for: POST /api/payments/create/
    """
    order_id = serializers.CharField(max_length=50, help_text="Order ID to pay for")
    payment_method = serializers.CharField(max_length=50, help_text="Payment method name")
    return_url = serializers.URLField(required=False, allow_blank=True, help_text="Return URL after payment")
    notify_url = serializers.URLField(required=False, allow_blank=True, help_text="Callback URL for payment notifications")
    
    def validate_payment_method(self, value):
        """Validate payment method exists and is active"""
        try:
            method = PaymentMethod.objects.get(name=value, is_active=True)
            return value
        except PaymentMethod.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive payment method")


class PaymentStatusSerializer(serializers.Serializer):
    """Serializer for payment status responses"""
    
    transaction_id = serializers.CharField()
    order_id = serializers.CharField()
    status = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    paid_at = serializers.DateTimeField(allow_null=True)
    error_message = serializers.CharField(allow_blank=True)
    
    # WeChat Pay specific fields
    wechat_transaction_id = serializers.CharField(allow_blank=True, required=False)
    wechat_prepay_id = serializers.CharField(allow_blank=True, required=False)


