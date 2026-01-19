"""
Points redemption serializers for validation and redemption operations.
"""
from rest_framework import serializers
from apps.common.validators import validate_points_amount
from .transaction_serializers import PointsExpirationSerializer, PointsTransactionSerializer


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




