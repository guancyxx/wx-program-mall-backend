"""
Points rules views.
"""
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import PointsRule
from ..serializers import PointsRuleSerializer


@api_view(['GET'])
def get_points_rules(request):
    """Get active points rules (public endpoint)"""
    try:
        rules = PointsRule.objects.filter(is_active=True)
        serializer = PointsRuleSerializer(rules, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

