"""
Points redemption views.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from decimal import Decimal

from ..services import PointsService, PointsIntegrationService
from ..serializers import (
    PointsRedemptionSerializer, PointsRedemptionValidationSerializer
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_points_redemption(request):
    """Validate points redemption request"""
    try:
        serializer = PointsRedemptionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Invalid input',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        points_amount = serializer.validated_data['points_amount']
        order_amount = serializer.validated_data['order_amount']
        
        validation_result = PointsIntegrationService.validate_points_redemption(
            user=request.user,
            points_amount=points_amount,
            order_amount=order_amount
        )
        
        response_serializer = PointsRedemptionValidationSerializer(validation_result)
        
        return Response({
            'success': True,
            'data': response_serializer.data
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def redeem_points(request):
    """Redeem points for discount"""
    try:
        serializer = PointsRedemptionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Invalid input',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        points_amount = serializer.validated_data['points_amount']
        order_amount = serializer.validated_data['order_amount']
        order_id = request.data.get('order_id')
        
        # Validate redemption first
        validation_result = PointsIntegrationService.validate_points_redemption(
            user=request.user,
            points_amount=points_amount,
            order_amount=order_amount
        )
        
        if not validation_result['is_valid']:
            return Response({
                'success': False,
                'message': 'Redemption validation failed',
                'errors': validation_result['errors']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Perform redemption
        with transaction.atomic():
            redemption_result = PointsService.redeem_points_for_discount(
                user=request.user,
                points_amount=points_amount,
                order_id=order_id
            )
        
        return Response({
            'success': True,
            'data': {
                'points_redeemed': redemption_result['points_redeemed'],
                'discount_amount': float(redemption_result['discount_amount']),
                'transaction_id': redemption_result['transaction'].id
            }
        })
    except ValueError as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_max_redeemable_points(request):
    """Get maximum points that can be redeemed for an order"""
    try:
        order_amount = request.GET.get('order_amount')
        if not order_amount:
            return Response({
                'success': False,
                'message': 'order_amount parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            order_amount = Decimal(str(order_amount))
        except:
            return Response({
                'success': False,
                'message': 'Invalid order_amount format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        max_points = PointsService.calculate_max_redeemable_points(
            user=request.user,
            order_amount=order_amount
        )
        
        return Response({
            'success': True,
            'data': {
                'max_redeemable_points': max_points,
                'max_discount_amount': float(Decimal(str(max_points)) / 100),
                'order_amount': float(order_amount)
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

