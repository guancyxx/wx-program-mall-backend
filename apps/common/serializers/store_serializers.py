"""
Store serializers for store management.
"""
from rest_framework import serializers
from ..models import Store


class StoreSerializer(serializers.ModelSerializer):
    """Serializer for store model matching Node.js Live schema"""
    
    # CamelCase field names for frontend compatibility
    startTime = serializers.CharField(source='start_time', allow_blank=True, required=False)
    endTime = serializers.CharField(source='end_time', allow_blank=True, required=False)
    createTime = serializers.DateTimeField(source='create_time', read_only=True)
    location = serializers.JSONField(required=False)
    img = serializers.CharField(max_length=500, allow_blank=True, required=False)
    
    class Meta:
        model = Store
        fields = [
            'id', 'location', 'name', 'address', 'detail', 'phone',
            'startTime', 'start_time', 'endTime', 'end_time',
            'status', 'img', 'createTime', 'create_time'
        ]
        read_only_fields = ['id', 'create_time']
    
    def to_representation(self, instance):
        """Convert to camelCase format for frontend compatibility"""
        data = super().to_representation(instance)
        # Remove duplicate underscore fields
        data.pop('start_time', None)
        data.pop('end_time', None)
        data.pop('create_time', None)
        return data
    
    def to_internal_value(self, data):
        """Convert from camelCase to snake_case and handle img field"""
        # Handle camelCase input
        if 'startTime' in data:
            data['start_time'] = data.pop('startTime')
        if 'endTime' in data:
            data['end_time'] = data.pop('endTime')
        
        # Handle img field: ensure it's a string
        if 'img' in data:
            img_value = data['img']
            if isinstance(img_value, dict):
                # Extract URL from object
                data['img'] = img_value.get('url') or img_value.get('imageUrl') or img_value.get('avatar_url') or ''
            elif isinstance(img_value, list) and len(img_value) > 0:
                # Extract URL from array
                first_item = img_value[0]
                if isinstance(first_item, dict):
                    data['img'] = first_item.get('url') or first_item.get('imageUrl') or first_item.get('avatar_url') or ''
                elif isinstance(first_item, str):
                    data['img'] = first_item
                else:
                    data['img'] = ''
            elif not isinstance(img_value, str):
                # Convert to string or empty string
                data['img'] = str(img_value) if img_value else ''
        
        return super().to_internal_value(data)


class StoreListSerializer(serializers.ModelSerializer):
    """Simplified serializer for store list"""
    
    startTime = serializers.CharField(source='start_time', read_only=True)
    endTime = serializers.CharField(source='end_time', read_only=True)
    createTime = serializers.DateTimeField(source='create_time', read_only=True)
    distance = serializers.SerializerMethodField()
    
    class Meta:
        model = Store
        fields = [
            'id', 'name', 'address', 'detail', 'phone',
            'startTime', 'endTime', 'status', 'img',
            'location', 'createTime', 'distance'
        ]
    
    def get_distance(self, obj):
        """Get distance if calculated"""
        return getattr(obj, '_distance', None)
    
    def to_representation(self, instance):
        """Convert to camelCase format"""
        data = super().to_representation(instance)
        return data

