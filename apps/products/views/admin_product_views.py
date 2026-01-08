"""
Admin product management views.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Q

from apps.common.utils import success_response, error_response
from ..models import Product
from ..serializers import (
    ProductCreateUpdateSerializer, AdminProductListSerializer
)


class AdminProductListView(APIView):
    """Admin product list endpoint - matches /api/goods/adminGetGoodslist"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Get query parameters matching Node.js API
            keyword = request.GET.get('keyword', '')
            status_filter = request.GET.get('status')
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('pageSize', 20))

            # Build query matching Node.js logic
            query = Q()

            if keyword:
                query &= Q(name__icontains=keyword) | Q(id__icontains=keyword)

            # status filter: 1=上架, 0=下架
            # None/null/empty = all products (no filter)
            if status_filter is not None and status_filter != '':
                status_value = int(status_filter)
                # 1 = 上架, 0 = 下架
                query &= Q(status=status_value)

            # Get products with prefetch for performance
            products = Product.objects.filter(query).prefetch_related(
                'images', 'product_tags'
            ).order_by(
                '-status', '-has_top', '-create_time'  # Match Node.js sorting
            )

            # Manual pagination to match Node.js format exactly
            total = products.count()
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            page_products = products[start_index:end_index]

            serializer = AdminProductListSerializer(page_products, many=True, context={'request': request})

            response_data = {
                "list": serializer.data,
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


class ProductCreateView(APIView):
    """Product creation endpoint - matches /api/goods/create"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            serializer = ProductCreateUpdateSerializer(data=request.data)
            if serializer.is_valid():
                product = serializer.save()
                return success_response({'id': product.id}, '创建成功')
            else:
                return error_response('数据验证失败', errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return error_response(f'创建商品失败: {str(e)}', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProductUpdateView(APIView):
    """Product update endpoint - matches /api/goods/updateGoods"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            product_id = request.data.get('id')
            if not product_id:
                return error_response('商品ID不能为空', status_code=status.HTTP_400_BAD_REQUEST)

            # Find existing product
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return error_response('商品不存在', status_code=status.HTTP_404_NOT_FOUND)

            serializer = ProductCreateUpdateSerializer(product, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return success_response(None, '更新成功')
            else:
                return error_response('数据验证失败', errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return error_response(f'更新商品失败: {str(e)}', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

