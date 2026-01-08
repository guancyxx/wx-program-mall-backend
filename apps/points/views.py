from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from decimal import Decimal

from .models import PointsAccount, PointsTransaction, PointsRule
from .services import PointsService, PointsIntegrationService
from .serializers import (
    PointsAccountListSerializer, PointsAccountSerializer,
    PointsTransactionListSerializer, PointsTransactionSerializer,
    PointsSummarySerializer, PointsRedemptionSerializer,
    PointsRedemptionValidationSerializer, PointsRuleSerializer
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


# Internal API endpoints (for integration with other apps)

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