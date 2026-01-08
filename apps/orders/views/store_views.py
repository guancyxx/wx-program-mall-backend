"""
Store-related views.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.common.utils import success_response, error_response


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

        # TODO: Implement store lookup with geospatial queries
        # This would require integration with the Live/Store model
        # For now, return mock data
        mock_store = {
            'lid': 1,
            'name': 'Mock Store',
            'address': 'Mock Address',
            'phone': '123-456-7890',
            'status': 1,
            'location': {
                'type': 'Point',
                'coordinates': [lng, lat]
            },
            'distance': 0.5  # Mock distance in km
        }

        return success_response(mock_store, 'Nearest store retrieved successfully')

    except Exception as e:
        return error_response(f"Server error: {str(e)}")

