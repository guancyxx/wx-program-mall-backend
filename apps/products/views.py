from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from .models import Product
from apps.common.utils import success_response


class ProductListView(APIView):
    """Product list endpoint"""
    permission_classes = [AllowAny]

    def get(self, request):
        # Placeholder implementation
        return success_response([], 'Product list retrieved')


class ProductDetailView(APIView):
    """Product detail endpoint"""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        # Placeholder implementation
        return success_response({}, 'Product detail retrieved')