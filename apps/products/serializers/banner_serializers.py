"""
Banner serializers.
"""
from rest_framework import serializers
from ..models import Banner


class BannerSerializer(serializers.ModelSerializer):
    """Serializer for banner data - matches frontend expected format"""
    
    class Meta:
        model = Banner
        fields = ['id', 'cover', 'title', 'type']

