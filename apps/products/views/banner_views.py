"""
Banner views.
"""
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from apps.common.utils import success_response, error_response
from ..models import Banner
from ..serializers import BannerSerializer


class GetBannersView(APIView):
    """Banner list endpoint - matches /api/goods/getBanners"""
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            # Get active banners ordered by order field
            banners = Banner.objects.filter(is_active=True).order_by('order', 'created_at')
            
            # Serialize banner data
            serializer = BannerSerializer(banners, many=True, context={'request': request})
            
            # Return in Node.js compatible format
            response_data = {
                'banner': serializer.data
            }
            
            return success_response(response_data, 'ok')
            
        except Exception as e:
            return error_response(f'获取轮播图失败: {str(e)}')

