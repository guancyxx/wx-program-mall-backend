"""
Product search and member-exclusive product views.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from django.db.models import Q

from apps.common.utils import success_response, error_response
from ..models import Product
from ..serializers import ProductListSerializer
from ..services import ProductMemberService


@api_view(['GET'])
@permission_classes([AllowAny])
def product_search(request):
    """Product search endpoint with enhanced search functionality"""
    try:
        query = request.GET.get('q', '').strip()
        if not query:
            return error_response('搜索关键词不能为空', status_code=status.HTTP_400_BAD_REQUEST)

        # Search in product name, description, and tags
        products = Product.objects.filter(
            Q(status=1) & (
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(content__icontains=query) |
                Q(product_tags__tag__icontains=query)
            )
        ).prefetch_related('images', 'product_tags').distinct()

        # Filter products based on member access
        products = ProductMemberService.filter_accessible_products(products, request.user)

        # Serialize with member-specific information
        serializer_data = []
        for product in products:
            product_data = ProductListSerializer(product).data
            member_info = ProductMemberService.get_product_with_member_info(product, request.user)
            product_data.update({
                'member_price': member_info['member_price'],
                'member_discount_rate': member_info['member_discount_rate'],
                'can_access': member_info['can_access'],
            })
            serializer_data.append(product_data)

        return success_response(serializer_data, '搜索成功')

    except Exception as e:
        return error_response(f'搜索失败: {str(e)}', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def member_exclusive_products(request):
    """Get member-exclusive products for authenticated users"""
    try:
        # Get products that are member-exclusive and accessible to user
        products = Product.objects.filter(
            status=1,
            is_member_exclusive=True
        ).prefetch_related('images', 'product_tags')

        # Filter based on user's tier
        accessible_products = ProductMemberService.filter_accessible_products(products, request.user)

        # Serialize with member-specific information
        serializer_data = []
        for product in accessible_products:
            product_data = ProductListSerializer(product).data
            member_info = ProductMemberService.get_product_with_member_info(product, request.user)
            product_data.update({
                'member_price': member_info['member_price'],
                'member_discount_rate': member_info['member_discount_rate'],
                'can_access': member_info['can_access'],
            })
            serializer_data.append(product_data)

        return success_response(serializer_data, '获取会员专享商品成功')

    except Exception as e:
        return error_response(f'获取会员专享商品失败: {str(e)}', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

