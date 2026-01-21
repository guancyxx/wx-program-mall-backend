"""
Tier upgrade log serializers for list and detail operations.
"""
from rest_framework import serializers
from ..models import TierUpgradeLog
from .tier_serializers import MembershipTierSerializer


class TierUpgradeLogListSerializer(serializers.ModelSerializer):
    """
    Serializer for tier upgrade log list view - minimal fields for list display.
    Used for: GET /api/membership/upgrade-history/
    """
    from_tier_name = serializers.CharField(source='from_tier.name', read_only=True)
    to_tier_name = serializers.CharField(source='to_tier.name', read_only=True)
    
    class Meta:
        model = TierUpgradeLog
        fields = ['from_tier_name', 'to_tier_name', 'spending_amount', 'created_at']
        read_only_fields = fields


class TierUpgradeLogSerializer(serializers.ModelSerializer):
    """
    Serializer for tier upgrade log detail view - complete fields for detail display.
    Used for: GET /api/membership/upgrade-history/{id}/
    """
    from_tier = MembershipTierSerializer(read_only=True)
    to_tier = MembershipTierSerializer(read_only=True)
    
    class Meta:
        model = TierUpgradeLog
        fields = ['from_tier', 'to_tier', 'reason', 'spending_amount', 'created_at']
        read_only_fields = fields







