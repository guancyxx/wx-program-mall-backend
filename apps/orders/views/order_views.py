"""
Order creation and query views.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.common.utils import success_response, error_response
from ..models import Order
from ..serializers import (
    OrderSerializer, OrderCreateSerializer, OrderListSerializer
)
from ..services import OrderService


class CreateOrderView(APIView):
    """Create order endpoint matching Node.js /api/order/createOrder"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Log incoming data for debugging
            logger.info(f"CreateOrder request data: {request.data}")
            
            serializer = OrderCreateSerializer(data=request.data)
            if not serializer.is_valid():
                logger.error(f"Serializer validation failed: {serializer.errors}")
                return error_response("Invalid order data", serializer.errors)

            # Create order using service
            order, error_msg = OrderService.create_order(request.user, serializer.validated_data)
            if not order:
                logger.error(f"Order creation failed: {error_msg}")
                return error_response(error_msg)

            # Get order details with applied benefits
            order_serializer = OrderSerializer(order)
            
            # Create payment transaction and get payment data
            from apps.payments.services import PaymentService
            
            # Get user's WeChat openid
            user_openid = getattr(request.user, 'wechat_openid', None)
            if not user_openid:
                logger.warning(f"User {request.user.id} does not have wechat_openid")
                # Try to get from order
                user_openid = order.openid or None
            
            if not user_openid:
                return error_response("User WeChat openid is required for payment")
            
            # Build notify URL
            notify_url = request.build_absolute_uri('/api/order/callback')
            
            payment_result = PaymentService.create_payment(
                user=request.user,
                order=order,
                payment_method='wechat_pay',
                notify_url=notify_url
            )
            
            if not payment_result['success']:
                logger.error(f"Payment creation failed: {payment_result['message']}")
                # Still return order, but without payment data
                # Frontend can handle this case
                return success_response({
                    'roid': order.roid,
                    'data': None,
                    'payment_error': payment_result['message'],
                    'order_details': {
                        'amount': float(order.amount),
                        'discounts_applied': len(order.discounts.all()),
                        'member_benefits': [
                            {
                                'type': discount.discount_type,
                                'amount': float(discount.discount_amount),
                                'description': discount.description
                            }
                            for discount in order.discounts.all()
                        ]
                    }
                }, 'Order created but payment initialization failed')
            
            # Get payment data for frontend
            payment_data = payment_result.get('payment_data', {})
            
            return success_response({
                'data': payment_data,
                'roid': order.roid,
                'order_details': {
                    'amount': float(order.amount),
                    'discounts_applied': len(order.discounts.all()),
                    'member_benefits': [
                        {
                            'type': discount.discount_type,
                            'amount': float(discount.discount_amount),
                            'description': discount.description
                        }
                        for discount in order.discounts.all()
                    ]
                }
            }, 'Order created successfully with member benefits applied')

        except Exception as e:
            return error_response(f"Server error: {str(e)}")


class GetMyOrderView(APIView):
    """Get user orders endpoint matching Node.js /api/order/getMyOrder"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Get query parameters
            filters = {
                'pageIndex': request.GET.get('pageIndex', 0),
                'pageSize': request.GET.get('pageSize', 10),
                'keyword': request.GET.get('keyword', ''),
                'status': request.GET.get('status', '0')
            }

            # Get orders using service
            orders = OrderService.get_user_orders(request.user, filters)
            
            # Serialize orders
            serializer = OrderListSerializer(orders, many=True)
            
            return success_response(serializer.data, 'Orders retrieved successfully')

        except Exception as e:
            return error_response(f"Server error: {str(e)}")


class GetOrderDetailView(APIView):
    """Get order detail endpoint matching Node.js /api/order/getOrderDetail"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            roid = request.GET.get('roid')
            if not roid:
                return error_response("Order ID (roid) is required")

            latitude = request.GET.get('latitude')
            longitude = request.GET.get('longitude')

            # Get order detail using service
            order_data, error_msg = OrderService.get_order_detail(
                request.user, roid, latitude, longitude
            )
            
            if not order_data:
                return error_response(error_msg)

            return success_response(order_data, 'Order detail retrieved successfully')

        except Exception as e:
            return error_response(f"Server error: {str(e)}")

