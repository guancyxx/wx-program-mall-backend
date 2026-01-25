"""
WeChat Pay specific serializers.
"""
from rest_framework import serializers
from ..models import WeChatPayment


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








