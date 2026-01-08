"""
Address serializers.
"""
from rest_framework import serializers
from ..models import Address


class AddressSerializer(serializers.ModelSerializer):
    """Address serializer"""
    
    class Meta:
        model = Address
        fields = ['id', 'name', 'phone', 'address', 'detail', 'address_type', 
                 'is_default', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

