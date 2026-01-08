"""
Store views for store management.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from apps.common.utils import success_response, error_response
from apps.common.models import Store
from apps.common.serializers.store_serializers import StoreSerializer, StoreListSerializer


class StoreListView(APIView):
    """Get list of stores"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get all active stores"""
        try:
            stores = Store.objects.filter(status=1).order_by('-create_time')
            serializer = StoreListSerializer(stores, many=True)
            return success_response(serializer.data, 'Stores retrieved successfully')
        except Exception as e:
            return error_response(f"Server error: {str(e)}")


class StoreDetailView(APIView):
    """Get store detail by lid"""
    permission_classes = [IsAuthenticated]

    def get(self, request, lid):
        """Get store detail by lid"""
        try:
            store = Store.objects.filter(lid=lid, status=1).first()
            if not store:
                return error_response("Store not found")
            
            serializer = StoreSerializer(store)
            return success_response(serializer.data, 'Store retrieved successfully')
        except Exception as e:
            return error_response(f"Server error: {str(e)}")

