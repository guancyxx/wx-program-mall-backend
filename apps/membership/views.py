from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import MembershipStatus, TierUpgradeLog
from .serializers import MembershipStatusSerializer, TierUpgradeLogSerializer
from apps.common.utils import success_response, error_response


class MembershipStatusView(APIView):
    """Get current membership status"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            membership = MembershipStatus.objects.get(user=request.user)
            serializer = MembershipStatusSerializer(membership)
            return success_response(serializer.data)
        except MembershipStatus.DoesNotExist:
            return error_response('Membership status not found')


class MembershipBenefitsView(APIView):
    """Get available membership benefits"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            membership = MembershipStatus.objects.get(user=request.user)
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
        upgrades = TierUpgradeLog.objects.filter(user=request.user)
        serializer = TierUpgradeLogSerializer(upgrades, many=True)
        return success_response(serializer.data)