"""
Banner views.
"""
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status

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


class SetHomeBannerView(APIView):
    """Set home banner endpoint - matches /api/admin/setHomeBanner"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            arr = request.data.get('arr', [])
            
            if not isinstance(arr, list):
                return error_response('arr must be a list', status_code=status.HTTP_400_BAD_REQUEST)
            
            # Delete all existing banners first
            Banner.objects.all().delete()
            
            # Create new banners from array
            created_banners = []
            for i, banner_data in enumerate(arr):
                banner = Banner.objects.create(
                    cover=banner_data.get('cover', ''),
                    title=banner_data.get('title', ''),
                    type=banner_data.get('type', 1),
                    order=i,
                    is_active=True
                )
                created_banners.append(banner)
            
            # Serialize and return created banners
            serializer = BannerSerializer(created_banners, many=True, context={'request': request})
            
            return success_response({'banner': serializer.data}, '轮播图设置成功')
            
        except Exception as e:
            return error_response(f'设置轮播图失败: {str(e)}', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
