"""
Membership tier serializers.
"""
from rest_framework import serializers
from ..models import MembershipTier


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








