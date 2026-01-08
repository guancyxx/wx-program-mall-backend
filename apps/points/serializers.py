from rest_framework import serializers
from apps.common.validators import validate_points_amount
from .models import PointsAccount, PointsTransaction, PointsExpiration, PointsRule


class PointsAccountListSerializer(serializers.ModelSerializer):
    """
    Serializer for points account list view - minimal fields for list display.
    Used for: GET /api/points/accounts/
    """
    
    class Meta:
        model = PointsAccount
        fields = ['total_points', 'available_points', 'created_at']
        read_only_fields = fields


class PointsAccountSerializer(serializers.ModelSerializer):
    """
    Serializer for points account detail view - complete fields for detail display.
    Used for: GET /api/points/accounts/{id}/
    """
    
    class Meta:
        model = PointsAccount
        fields = [
            'total_points', 'available_points', 'lifetime_earned', 
            'lifetime_redeemed', 'created_at', 'updated_at'
        ]
        read_only_fields = fields


class PointsTransactionListSerializer(serializers.ModelSerializer):
    """
    Serializer for points transaction list view - minimal fields for list display.
    Used for: GET /api/points/transactions/
    """
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    
    class Meta:
        model = PointsTransaction
        fields = [
            'id', 'transaction_type', 'transaction_type_display', 'amount', 
            'balance_after', 'created_at'
        ]
        read_only_fields = fields


class PointsTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for points transaction detail view - complete fields for detail display.
    Used for: GET /api/points/transactions/{id}/
    """
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
    """
    Serializer for points redemption requests.
    Used for: POST /api/points/redeem/
    """
    points_amount = serializers.IntegerField(
        min_value=500,
        validators=[validate_points_amount],
        help_text="Points amount (must be multiple of 100, minimum 500)"
    )
    order_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        help_text="Order amount for redemption calculation"
    )


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