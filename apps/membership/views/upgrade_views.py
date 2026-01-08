"""
Tier upgrade history views.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.common.utils import success_response
from ..models import TierUpgradeLog
from ..serializers import TierUpgradeLogListSerializer


class TierUpgradeHistoryView(APIView):
    """Get tier upgrade history"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Use select_related to avoid N+1 query and list serializer for list view
        upgrades = TierUpgradeLog.objects.select_related('from_tier', 'to_tier').filter(user=request.user)
        serializer = TierUpgradeLogListSerializer(upgrades, many=True)
        return success_response(serializer.data)

