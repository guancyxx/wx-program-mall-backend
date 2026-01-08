"""
Address serializers with RESTful API design.
"""
from rest_framework import serializers
from ..models import Address


class AddressSerializer(serializers.ModelSerializer):
    """
    Address serializer for RESTful API.
    
    Fields:
    - id: Address ID
    - name: Recipient name
    - phone: Contact phone
    - address: General address
    - detail: Detailed address
    - address_type: Address type (0=家, 1=公司, 2=学校, 3=其他)
    - is_default: Whether this is the default address
    - created_at: Creation timestamp
    - updated_at: Update timestamp
    """
    
    class Meta:
        model = Address
        fields = [
            'id', 'name', 'phone', 'address', 'detail', 
            'address_type', 'is_default', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_address_type(self, value):
        """Validate address_type is in valid range"""
        if value not in [0, 1, 2, 3]:
            raise serializers.ValidationError('address_type must be 0, 1, 2, or 3')
        return value
    
    def validate_phone(self, value):
        """Validate phone number format"""
        if not value:
            raise serializers.ValidationError('Phone number is required')
        # Basic phone validation (can be enhanced)
        if len(value) < 11:
            raise serializers.ValidationError('Phone number must be at least 11 digits')
        return value
    
    def validate_name(self, value):
        """Validate name"""
        if not value:
            raise serializers.ValidationError('Name is required')
        if len(value) < 2:
            raise serializers.ValidationError('Name must be at least 2 characters')
        return value
