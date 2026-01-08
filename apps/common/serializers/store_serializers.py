"""
Store serializers for store management.
"""
from rest_framework import serializers
from ..models import Store


class StoreSerializer(serializers.ModelSerializer):
    """Serializer for store model matching Node.js Live schema"""
    
    # CamelCase field names for frontend compatibility
    lid = serializers.IntegerField(read_only=True, required=False)
    startTime = serializers.CharField(source='start_time', allow_blank=True, required=False)
    endTime = serializers.CharField(source='end_time', allow_blank=True, required=False)
    createTime = serializers.DateTimeField(source='create_time', read_only=True)
    location = serializers.JSONField(required=False)
    
    class Meta:
        model = Store
        fields = [
            'lid', 'location', 'name', 'address', 'detail', 'phone',
            'startTime', 'start_time', 'endTime', 'end_time',
            'status', 'img', 'createTime', 'create_time'
        ]
        read_only_fields = ['lid', 'create_time']
    
    def to_representation(self, instance):
        """Convert to camelCase format for frontend compatibility"""
        data = super().to_representation(instance)
        # Remove duplicate underscore fields
        data.pop('start_time', None)
        data.pop('end_time', None)
        data.pop('create_time', None)
        return data
    
    def to_internal_value(self, data):
        """Convert from camelCase to snake_case"""
        # Handle camelCase input
        if 'startTime' in data:
            data['start_time'] = data.pop('startTime')
        if 'endTime' in data:
            data['end_time'] = data.pop('endTime')
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
            'lid', 'name', 'address', 'detail', 'phone',
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

