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
    """Get stores list sorted by distance - supports pagination"""
    try:
        latitude = request.GET.get('latitude')
        longitude = request.GET.get('longitude')
        page_index = int(request.GET.get('pageIndex', 0))
        page_size = int(request.GET.get('pageSize', 20))

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
        
        # Calculate distance for each store and create list with distance
        stores_with_distance = []
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Searching for stores from lat={lat}, lng={lng}")
        logger.debug(f"Found {stores.count()} active stores")
        
        for store in stores:
            store_lon, store_lat = store.get_coordinates()
            if store_lon is None or store_lat is None:
                logger.debug(f"Store {store.id} has invalid coordinates, skipping")
                continue
            
            distance = store.calculate_distance(lat, lng)
            if distance is not None:
                stores_with_distance.append((store, distance))
        
        if not stores_with_distance:
            logger.warning("No stores found with valid location data")
            return error_response("No stores found with valid location data")
        
        # Sort by distance (nearest first)
        stores_with_distance.sort(key=lambda x: x[1])
        
        # Apply pagination
        total_count = len(stores_with_distance)
        start_index = page_index * page_size
        end_index = start_index + page_size
        paginated_stores = stores_with_distance[start_index:end_index]
        
        # Set distance on store objects and serialize
        store_list = []
        for store, distance in paginated_stores:
            store._distance = distance
            serializer = StoreListSerializer(store, context={'request': request})
            store_data = serializer.data
            store_data['distance'] = distance
            store_list.append(store_data)
        
        # Return data in format matching Node.js API (list format)
        response_data = {
            'list': store_list,
            'count': total_count
        }
        
        logger.debug(f"Returning {len(store_list)} stores (page {page_index}, total {total_count})")

        return success_response(response_data, 'Stores retrieved successfully')

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting stores: {e}")
        return error_response(f"Server error: {str(e)}")

