from rest_framework import serializers
from .models import PaymentMethod, PaymentTransaction, RefundRequest, WeChatPayment


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for payment methods"""
    
    class Meta:
        model = PaymentMethod
        fields = ['name', 'display_name', 'is_active', 'config']
        read_only_fields = ['name']


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """Serializer for payment transactions"""
    
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
    """Serializer for creating payment transactions"""
    
    order_id = serializers.CharField(max_length=50, help_text="Order ID to pay for")
    payment_method = serializers.CharField(max_length=50, help_text="Payment method name")
    return_url = serializers.URLField(required=False, help_text="Return URL after payment")
    notify_url = serializers.URLField(required=False, help_text="Callback URL for payment notifications")
    
    def validate_payment_method(self, value):
        """Validate payment method exists and is active"""
        try:
            method = PaymentMethod.objects.get(name=value, is_active=True)
            return value
        except PaymentMethod.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive payment method")


class RefundRequestSerializer(serializers.ModelSerializer):
    """Serializer for refund requests"""
    
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
    """Serializer for creating refund requests"""
    
    transaction_id = serializers.CharField(max_length=100, help_text="Original transaction ID")
    refund_amount = serializers.DecimalField(max_digits=10, decimal_places=2, help_text="Refund amount")
    refund_reason = serializers.CharField(max_length=500, help_text="Reason for refund")
    refund_type = serializers.ChoiceField(
        choices=RefundRequest.REFUND_TYPE_CHOICES,
        default='full',
        help_text="Type of refund"
    )
    return_order_id = serializers.CharField(
        max_length=50, 
        required=False, 
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
        if value <= 0:
            raise serializers.ValidationError("Refund amount must be greater than 0")
        return value


class WeChatPaymentSerializer(serializers.ModelSerializer):
    """Serializer for WeChat Pay specific data"""
    
    class Meta:
        model = WeChatPayment
        fields = [
            'appid', 'mch_id', 'body', 'out_trade_no', 'total_fee',
            'prepay_id', 'code_url', 'transaction_id', 'bank_type',
            'sign', 'sign_type', 'created_at'
        ]
        read_only_fields = [
            'prepay_id', 'code_url', 'transaction_id', 'bank_type',
            'sign', 'created_at'
        ]


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


class PaymentCallbackSerializer(serializers.Serializer):
    """Serializer for processing payment callbacks"""
    
    # This will be customized based on the payment method
    # WeChat Pay callback fields
    appid = serializers.CharField(required=False)
    mch_id = serializers.CharField(required=False)
    nonce_str = serializers.CharField(required=False)
    sign = serializers.CharField(required=False)
    result_code = serializers.CharField(required=False)
    return_code = serializers.CharField(required=False)
    out_trade_no = serializers.CharField(required=False)
    transaction_id = serializers.CharField(required=False)
    total_fee = serializers.IntegerField(required=False)
    cash_fee = serializers.IntegerField(required=False)
    bank_type = serializers.CharField(required=False)
    time_end = serializers.CharField(required=False)
    
    def validate(self, attrs):
        """Validate callback data based on payment method"""
        # This would be implemented based on specific payment method requirements
        return attrs