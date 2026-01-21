"""
Membership status serializers for list and detail operations.
"""
from rest_framework import serializers
from ..models import MembershipStatus
from .tier_serializers import MembershipTierSerializer


class MembershipStatusListSerializer(serializers.ModelSerializer):
    """
    Serializer for membership status list view - minimal fields for list display.
    Used for: GET /api/membership/statuses/
    """
    tier_name = serializers.CharField(source='tier.name', read_only=True)
    tier_display_name = serializers.CharField(source='tier.display_name', read_only=True)
    
    class Meta:
        model = MembershipStatus
        fields = ['tier_name', 'tier_display_name', 'total_spending', 'created_at']
        read_only_fields = fields


class MembershipStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for membership status detail view - complete fields for detail display.
    Used for: GET /api/membership/status/{id}/
    """
    tier = MembershipTierSerializer(read_only=True)
    
    class Meta:
        model = MembershipStatus
        fields = ['tier', 'total_spending', 'tier_start_date', 'created_at']
        read_only_fields = fields







