from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import MembershipStatus, TierUpgradeLog
from .serializers import (
    MembershipStatusListSerializer, MembershipStatusSerializer,
    TierUpgradeLogListSerializer, TierUpgradeLogSerializer
)
from apps.common.utils import success_response, error_response


class MembershipStatusView(APIView):
    """Get current membership status"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Use select_related to avoid N+1 query
            membership = MembershipStatus.objects.select_related('tier').get(user=request.user)
            serializer = MembershipStatusSerializer(membership)
            return success_response(serializer.data)
        except MembershipStatus.DoesNotExist:
            return error_response('Membership status not found')


class MembershipBenefitsView(APIView):
    """Get available membership benefits"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Use select_related to avoid N+1 query
            membership = MembershipStatus.objects.select_related('tier').get(user=request.user)
            benefits = membership.tier.benefits
            return success_response({
                'tier': membership.tier.name,
                'benefits': benefits,
                'points_multiplier': float(membership.tier.points_multiplier)
            })
        except MembershipStatus.DoesNotExist:
            return error_response('Membership status not found')


class TierUpgradeHistoryView(APIView):
    """Get tier upgrade history"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Use select_related to avoid N+1 query and list serializer for list view
        upgrades = TierUpgradeLog.objects.select_related('from_tier', 'to_tier').filter(user=request.user)
        serializer = TierUpgradeLogListSerializer(upgrades, many=True)
        return success_response(serializer.data)