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
        try:
            serializer = OrderCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response("Invalid order data", serializer.errors)

            # Create order using service
            order, error_msg = OrderService.create_order(request.user, serializer.validated_data)
            if not order:
                return error_response(error_msg)

            # Get order details with applied benefits
            order_serializer = OrderSerializer(order)
            
            # TODO: Integrate with WeChat Pay API
            # For now, return mock payment data
            payment_data = {
                'appId': 'wx23fedab0e057b533',  # Mock data
                'timeStamp': '1234567890',
                'nonceStr': 'randomstring',
                'package': 'prepay_id=mock_prepay_id',
                'signType': 'RSA',
                'paySign': 'mock_signature'
            }

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

