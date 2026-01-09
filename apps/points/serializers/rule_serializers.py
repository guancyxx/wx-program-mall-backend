"""
Points rule serializers.
"""
from rest_framework import serializers
from ..models import PointsRule


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



