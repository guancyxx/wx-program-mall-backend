from rest_framework import serializers
from .models import MembershipTier, MembershipStatus, TierUpgradeLog


class MembershipTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = MembershipTier
        fields = ['name', 'display_name', 'min_spending', 'max_spending', 
                 'points_multiplier', 'benefits']


class MembershipStatusSerializer(serializers.ModelSerializer):
    tier = MembershipTierSerializer(read_only=True)
    
    class Meta:
        model = MembershipStatus
        fields = ['tier', 'total_spending', 'tier_start_date', 'created_at']


class TierUpgradeLogSerializer(serializers.ModelSerializer):
    from_tier = MembershipTierSerializer(read_only=True)
    to_tier = MembershipTierSerializer(read_only=True)
    
    class Meta:
        model = TierUpgradeLog
        fields = ['from_tier', 'to_tier', 'reason', 'spending_amount', 'created_at']