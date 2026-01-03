from rest_framework import serializers
from .models import PointsAccount, PointsTransaction, PointsExpiration, PointsRule


class PointsAccountSerializer(serializers.ModelSerializer):
    """Serializer for points account"""
    
    class Meta:
        model = PointsAccount
        fields = [
            'total_points', 'available_points', 'lifetime_earned', 
            'lifetime_redeemed', 'created_at', 'updated_at'
        ]
        read_only_fields = fields


class PointsTransactionSerializer(serializers.ModelSerializer):
    """Serializer for points transactions"""
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    
    class Meta:
        model = PointsTransaction
        fields = [
            'id', 'transaction_type', 'transaction_type_display', 'amount', 
            'balance_after', 'description', 'reference_id', 'created_at'
        ]
        read_only_fields = fields


class PointsExpirationSerializer(serializers.ModelSerializer):
    """Serializer for points expiration records"""
    
    class Meta:
        model = PointsExpiration
        fields = [
            'points_amount', 'remaining_points', 'earned_date', 
            'expiry_date', 'is_expired', 'is_expiring_soon'
        ]
        read_only_fields = fields


class PointsRedemptionSerializer(serializers.Serializer):
    """Serializer for points redemption requests"""
    points_amount = serializers.IntegerField(min_value=500)
    order_amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    
    def validate_points_amount(self, value):
        if value % 100 != 0:
            raise serializers.ValidationError("Points must be in multiples of 100")
        return value


class PointsSummarySerializer(serializers.Serializer):
    """Serializer for points summary response"""
    available_points = serializers.IntegerField()
    total_points = serializers.IntegerField()
    lifetime_earned = serializers.IntegerField()
    lifetime_redeemed = serializers.IntegerField()
    expiring_soon = serializers.IntegerField()
    expiring_records = PointsExpirationSerializer(many=True)
    recent_transactions = PointsTransactionSerializer(many=True)


class PointsRedemptionValidationSerializer(serializers.Serializer):
    """Serializer for points redemption validation response"""
    is_valid = serializers.BooleanField()
    errors = serializers.ListField(child=serializers.CharField())
    max_redeemable = serializers.IntegerField()
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class PointsRuleSerializer(serializers.ModelSerializer):
    """Serializer for points rules"""
    rule_type_display = serializers.CharField(source='get_rule_type_display', read_only=True)
    
    class Meta:
        model = PointsRule
        fields = [
            'id', 'rule_type', 'rule_type_display', 'points_amount', 
            'is_percentage', 'min_order_amount', 'max_points_per_transaction',
            'is_active', 'description'
        ]
        read_only_fields = ['id', 'rule_type_display']