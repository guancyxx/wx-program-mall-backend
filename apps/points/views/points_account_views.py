"""
Points account query views.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import PointsAccount
from ..services import PointsService
from ..serializers import (
    PointsAccountListSerializer, PointsAccountSerializer,
    PointsTransactionListSerializer, PointsSummarySerializer
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_points_balance(request):
    """Get user's current points balance"""
    try:
        account = PointsService.get_or_create_account(request.user)
        serializer = PointsAccountSerializer(account)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_points_summary(request):
    """Get comprehensive points summary for user"""
    try:
        summary = PointsService.get_points_summary(request.user)
        serializer = PointsSummarySerializer(summary)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_points_transactions(request):
    """Get user's points transaction history"""
    try:
        account = PointsService.get_or_create_account(request.user)
        
        # Pagination parameters
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        
        # Filter parameters
        transaction_type = request.GET.get('type')
        
        # Use select_related/prefetch_related to avoid N+1 queries
        transactions = account.transactions.all()
        
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)
        
        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated_transactions = transactions[start:end]
        
        # Use list serializer for list view
        serializer = PointsTransactionListSerializer(paginated_transactions, many=True)
        
        return Response({
            'success': True,
            'data': {
                'transactions': serializer.data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': transactions.count(),
                    'has_next': end < transactions.count()
                }
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

