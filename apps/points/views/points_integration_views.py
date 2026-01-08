"""
Points integration views (internal API endpoints for other apps).
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from decimal import Decimal

from ..services import PointsService, PointsIntegrationService


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def award_review_points(request):
    """Award points for product review (called by products app)"""
    try:
        product_id = request.data.get('product_id')
        if not product_id:
            return Response({
                'success': False,
                'message': 'product_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        transaction = PointsService.award_review_points(
            user=request.user,
            product_id=product_id
        )
        
        if transaction:
            return Response({
                'success': True,
                'data': {
                    'points_awarded': transaction.amount,
                    'transaction_id': transaction.id
                }
            })
        else:
            return Response({
                'success': False,
                'message': 'Points already awarded for this review or rule not found'
            }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def internal_award_purchase_points(request):
    """Internal endpoint to award points for purchase (called by orders app)"""
    try:
        user_id = request.data.get('user_id')
        order_amount = request.data.get('order_amount')
        order_id = request.data.get('order_id')
        is_first_purchase = request.data.get('is_first_purchase', False)
        
        if not all([user_id, order_amount]):
            return Response({
                'success': False,
                'message': 'user_id and order_amount are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        transactions = PointsIntegrationService.handle_order_completion(
            user=user,
            order_amount=Decimal(str(order_amount)),
            order_id=order_id,
            is_first_purchase=is_first_purchase
        )
        
        total_points = sum(t.amount for t in transactions)
        
        return Response({
            'success': True,
            'data': {
                'total_points_awarded': total_points,
                'transactions': [
                    {
                        'id': t.id,
                        'amount': t.amount,
                        'description': t.description
                    } for t in transactions
                ]
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def internal_award_registration_points(request):
    """Internal endpoint to award points for registration (called by users app)"""
    try:
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response({
                'success': False,
                'message': 'user_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        transaction = PointsIntegrationService.handle_user_registration(user)
        
        if transaction:
            return Response({
                'success': True,
                'data': {
                    'points_awarded': transaction.amount,
                    'transaction_id': transaction.id
                }
            })
        else:
            return Response({
                'success': False,
                'message': 'Registration points rule not found'
            }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

