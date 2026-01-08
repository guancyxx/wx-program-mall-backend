"""
Membership status views.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.common.utils import success_response, error_response
from ..models import MembershipStatus
from ..serializers import MembershipStatusSerializer


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

