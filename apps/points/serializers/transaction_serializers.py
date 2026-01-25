"""
Points transaction serializers for list, detail, and expiration operations.
"""
from rest_framework import serializers
from ..models import PointsTransaction, PointsExpiration


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








