"""
Points account serializers for list and detail operations.
"""
from rest_framework import serializers
from ..models import PointsAccount


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



