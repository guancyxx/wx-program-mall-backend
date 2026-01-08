"""
Store-related views.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import math

from apps.common.utils import success_response, error_response
from apps.common.models import Store
from apps.common.serializers.store_serializers import StoreListSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_nearest_store(request):
    """Get nearest store endpoint matching Node.js /api/order/getLive"""
    try:
        latitude = request.GET.get('latitude')
        longitude = request.GET.get('longitude')

        if not latitude or not longitude:
            return error_response("Latitude and longitude parameters are required")

        try:
            lat = float(latitude)
            lng = float(longitude)
            
            # Validate coordinates
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                return error_response("Invalid latitude or longitude format")
                
        except ValueError:
            return error_response("Invalid latitude or longitude format")

        # Get active stores
        stores = Store.objects.filter(status=1)
        
        if not stores.exists():
            return error_response("No active stores found")
        
        # Calculate distance to each store and find nearest
        nearest_store = None
        min_distance = float('inf')
        
        for store in stores:
            distance = store.calculate_distance(lat, lng)
            if distance is not None and distance < min_distance:
                min_distance = distance
                nearest_store = store
        
        if not nearest_store:
            return error_response("No stores found with valid location data")
        
        # Set distance on store object for serializer
        nearest_store._distance = min_distance
        
        # Serialize store data
        serializer = StoreListSerializer(nearest_store)
        store_data = serializer.data
        
        # Ensure distance is included
        store_data['distance'] = min_distance

        return success_response(store_data, 'Nearest store retrieved successfully')

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting nearest store: {e}")
        return error_response(f"Server error: {str(e)}")

