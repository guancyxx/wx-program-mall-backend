"""
Payment method serializers.
"""
from rest_framework import serializers
from ..models import PaymentMethod


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for payment methods"""
    
    class Meta:
        model = PaymentMethod
        fields = ['name', 'display_name', 'is_active', 'config']
        read_only_fields = ['name']


