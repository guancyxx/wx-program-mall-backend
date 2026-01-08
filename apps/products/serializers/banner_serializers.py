"""
Banner serializers.
"""
from rest_framework import serializers
from ..models import Banner


class BannerSerializer(serializers.ModelSerializer):
    """Serializer for banner data - matches frontend expected format"""
    cover = serializers.SerializerMethodField()
    
    class Meta:
        model = Banner
        fields = ['id', 'cover', 'title', 'type']
    
    def get_cover(self, obj):
        """Return full URL for banner image"""
        request = self.context.get('request')
        
        # If already a full URL, return as-is
        if obj.cover.startswith('http://') or obj.cover.startswith('https://'):
            return obj.cover
        
        # Build absolute URL from relative path
        if request:
            return request.build_absolute_uri(obj.cover)
        
        # Fallback to settings
        from django.conf import settings
        backend_url = getattr(settings, 'BACKEND_URL', 'http://localhost:8000').rstrip('/')
        image_path = obj.cover if obj.cover.startswith('/') else f'/{obj.cover}'
        return f"{backend_url}{image_path}"


