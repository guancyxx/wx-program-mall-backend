"""
Product list and detail views.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Q

from apps.common.utils import success_response, error_response
from ..models import Product
from ..serializers import ProductListSerializer, ProductDetailSerializer
from ..services import ProductMemberService


class ProductListView(APIView):
    """Product list endpoint - GET /api/products/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Get query parameters matching Node.js API
            keyword = request.GET.get('keyword', '')
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('pageSize', 20))
            has_recommend = request.GET.get('hasRecommend')
            tags = request.GET.get('tags', '')

            # Build query matching Node.js logic
            query = Q(status=1)  # Only active products

            if keyword:
                query &= Q(name__icontains=keyword) | Q(description__icontains=keyword)

            if has_recommend:
                query &= Q(has_recommend=1)

            if tags:
                tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
                if tag_list:
                    query &= Q(product_tags__tag__in=tag_list)

            # Get products with prefetch for performance
            products = Product.objects.filter(query).prefetch_related(
                'images', 'product_tags'
            ).distinct()

            # Filter products based on member access
            products = ProductMemberService.filter_accessible_products(products, request.user)

            # Apply sorting matching Node.js logic
            products = products.order_by('-has_top', '-has_recommend', '-create_time')

            # Manual pagination to match Node.js format exactly
            total = products.count()
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            page_products = products[start_index:end_index]

            # Serialize with member-specific information
            serializer_data = []
            for product in page_products:
                product_data = ProductListSerializer(product, context={'request': request}).data
                # Add member-specific pricing and access info
                member_info = ProductMemberService.get_product_with_member_info(product, request.user)
                product_data.update({
                    'member_price': member_info['member_price'],
                    'member_discount_rate': member_info['member_discount_rate'],
                    'can_access': member_info['can_access'],
                })
                serializer_data.append(product_data)

            response_data = {
                "list": serializer_data,
                "page": {
                    "pageNum": page,
                    "pageSize": page_size,
                    "total": total,
                    "totalPages": (total + page_size - 1) // page_size
                }
            }

            return success_response(response_data, '获取商品列表成功')

        except Exception as e:
            return error_response(f'获取商品列表失败: {str(e)}', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProductDetailView(APIView):
    """Product detail endpoint - GET /api/products/{id}/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, id=None):
        try:
            # RESTful API uses path parameter (Django primary key id)
            if not id:
                return error_response('商品ID不能为空', status_code=status.HTTP_400_BAD_REQUEST)

            # Find product by Django primary key id
            try:
                product = Product.objects.prefetch_related(
                    'images', 'product_tags', 'category'
                ).get(id=id)
            except Product.DoesNotExist:
                return error_response('商品不存在', status_code=status.HTTP_404_NOT_FOUND)

            # Check product status matching Node.js logic
            if product.status != 1:
                return error_response('商品已下架', status_code=status.HTTP_400_BAD_REQUEST)

            # Check member access for exclusive products
            if not ProductMemberService.can_access_product(product, request.user):
                return error_response('该商品仅限会员访问', status_code=status.HTTP_403_FORBIDDEN)

            # Increment view count matching Node.js behavior
            product.views += 1
            product.save(update_fields=['views'])

            # Get product data with member-specific information
            product_data = ProductDetailSerializer(product, context={'request': request}).data
            member_info = ProductMemberService.get_product_with_member_info(product, request.user)
            product_data.update({
                'member_price': member_info['member_price'],
                'member_discount_rate': member_info['member_discount_rate'],
                'can_access': member_info['can_access'],
                'user_tier_level': member_info['user_tier_level'],
            })

            return success_response(product_data, '获取商品详情成功')

        except Exception as e:
            return error_response(f'获取商品详情失败: {str(e)}', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

