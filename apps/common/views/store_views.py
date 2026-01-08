"""
Store views for store management.
RESTful API endpoints for store CRUD operations.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db import transaction, models

from apps.common.utils import success_response, error_response
from apps.common.models import Store
from apps.common.serializers.store_serializers import StoreSerializer, StoreListSerializer


class StoreListView(APIView):
    """RESTful API for store list and creation"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get list of stores with optional filtering"""
        try:
            # Get query parameters
            keyword = request.GET.get('keyword', '')
            page_index = int(request.GET.get('pageIndex', 0))
            page_size = int(request.GET.get('pageSize', 20))
            
            # Build query
            stores = Store.objects.filter(status=1)
            
            # Apply keyword search
            if keyword:
                stores = stores.filter(
                    name__icontains=keyword
                ) | stores.filter(
                    address__icontains=keyword
                ) | stores.filter(
                    lid__icontains=keyword
                )
            
            # Order by create_time descending
            stores = stores.order_by('-create_time')
            
            # Get total count
            total_count = stores.count()
            
            # Apply pagination
            start_index = page_index * page_size
            end_index = start_index + page_size
            page_stores = stores[start_index:end_index]
            
            serializer = StoreListSerializer(page_stores, many=True)
            
            # Return data in format matching Node.js API
            response_data = {
                'list': serializer.data,
                'count': total_count
            }
            
            return success_response(response_data, 'Stores retrieved successfully')
        except Exception as e:
            return error_response(f"Server error: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """Create a new store"""
        try:
            data = request.data.copy()
            
            # Handle location from longitude/latitude
            if 'longitude' in data and 'latitude' in data:
                longitude = float(data.pop('longitude'))
                latitude = float(data.pop('latitude'))
                data['location'] = {
                    'type': 'Point',
                    'coordinates': [longitude, latitude]
                }
            
            # Generate lid if not provided (auto-increment from max lid + 1)
            if 'lid' not in data or not data.get('lid'):
                max_lid = Store.objects.aggregate(max_lid=models.Max('lid'))['max_lid']
                if max_lid is None:
                    data['lid'] = 100001  # Start from 100001 like Node.js
                else:
                    data['lid'] = max_lid + 1
            
            serializer = StoreSerializer(data=data)
            if serializer.is_valid():
                store = serializer.save()
                return success_response(StoreSerializer(store).data, 'Store created successfully')
            else:
                return error_response('Validation failed', errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return error_response(f"Server error: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StoreDetailView(APIView):
    """RESTful API for store detail, update, and delete"""
    permission_classes = [IsAuthenticated]

    def get(self, request, lid):
        """Get store detail by lid"""
        try:
            store = Store.objects.filter(lid=lid, status=1).first()
            if not store:
                return error_response("Store not found", status_code=status.HTTP_404_NOT_FOUND)
            
            serializer = StoreSerializer(store)
            return success_response(serializer.data, 'Store retrieved successfully')
        except Exception as e:
            return error_response(f"Server error: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, lid):
        """Update store by lid"""
        try:
            store = Store.objects.filter(lid=lid).first()
            if not store:
                return error_response("Store not found", status_code=status.HTTP_404_NOT_FOUND)
            
            data = request.data.copy()
            
            # Handle location from longitude/latitude
            if 'longitude' in data and 'latitude' in data:
                longitude = float(data.pop('longitude'))
                latitude = float(data.pop('latitude'))
                data['location'] = {
                    'type': 'Point',
                    'coordinates': [longitude, latitude]
                }
            
            # Remove lid from update data (lid should not be changed)
            data.pop('lid', None)
            
            serializer = StoreSerializer(store, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return success_response(StoreSerializer(store).data, 'Store updated successfully')
            else:
                return error_response('Validation failed', errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return error_response(f"Server error: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request, lid):
        """Partial update store by lid"""
        return self.put(request, lid)

    def delete(self, request, lid):
        """Delete store by lid (soft delete: set status=2)"""
        try:
            store = Store.objects.filter(lid=lid).first()
            if not store:
                return error_response("Store not found", status_code=status.HTTP_404_NOT_FOUND)
            
            # Soft delete: set status to 2
            store.status = 2
            store.save()
            
            return success_response(None, 'Store deleted successfully')
        except Exception as e:
            return error_response(f"Server error: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

