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
        
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Searching for nearest store from lat={lat}, lng={lng}")
        logger.debug(f"Found {stores.count()} active stores")
        
        for store in stores:
            logger.debug(f"Checking store {store.id}: {store.name}, location={store.location}")
            store_lon, store_lat = store.get_coordinates()
            logger.debug(f"Store coordinates: lon={store_lon}, lat={store_lat}")
            
            distance = store.calculate_distance(lat, lng)
            logger.debug(f"Distance calculated: {distance}")
            
            if distance is not None and distance < min_distance:
                min_distance = distance
                nearest_store = store
                logger.debug(f"New nearest store: {store.name} at {distance}km")
        
        if not nearest_store:
            logger.warning("No stores found with valid location data")
            return error_response("No stores found with valid location data")
        
        # Set distance on store object for serializer
        nearest_store._distance = min_distance
        
        # Serialize store data with request context for image URL conversion
        serializer = StoreListSerializer(nearest_store, context={'request': request})
        store_data = serializer.data
        
        # Ensure distance is included
        store_data['distance'] = min_distance
        
        logger.debug(f"Returning nearest store: {nearest_store.name} at {min_distance}km")

        return success_response(store_data, 'Nearest store retrieved successfully')

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting nearest store: {e}")
        return error_response(f"Server error: {str(e)}")

