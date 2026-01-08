from rest_framework import serializers
from .models import MembershipTier, MembershipStatus, TierUpgradeLog


class MembershipTierSerializer(serializers.ModelSerializer):
    """
    Serializer for membership tier information.
    Used for nested serialization in membership status and upgrade logs.
    """
    class Meta:
        model = MembershipTier
        fields = ['name', 'display_name', 'min_spending', 'max_spending', 
                 'points_multiplier', 'benefits']
        read_only_fields = fields


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