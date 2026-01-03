from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from apps.common.utils import success_response


class OrderListView(APIView):
    """Order list endpoint"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Placeholder implementation
        return success_response([], 'Order list retrieved')