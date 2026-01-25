"""
Order action serializers for refund, cancel, and payment operations.
"""
from rest_framework import serializers
from ..models import ReturnOrder


class ReturnOrderSerializer(serializers.ModelSerializer):
    """Serializer for return orders"""
    
    class Meta:
        model = ReturnOrder
        fields = [
            'rrid', 'gid', 'uid', 'roid', 'amount', 'refund_amount',
            'status', 'create_time', 'openid'
        ]
        read_only_fields = ['rrid', 'create_time']


class OrderRefundSerializer(serializers.Serializer):
    """Serializer for order refund requests"""
    
    roid = serializers.CharField(max_length=50)
    reason = serializers.CharField(max_length=500)
    rrid = serializers.CharField(max_length=50)

    def validate_reason(self, value):
        """Validate refund reason"""
        if not value.strip():
            raise serializers.ValidationError("Refund reason cannot be empty")
        return value


class OrderCancelSerializer(serializers.Serializer):
    """Serializer for order cancellation"""
    
    roid = serializers.CharField(max_length=50)


class OrderPaymentSerializer(serializers.Serializer):
    """Serializer for payment-related operations"""
    
    roid = serializers.CharField(max_length=50)








