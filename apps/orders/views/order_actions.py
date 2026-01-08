"""
Order action views (cancel, refund, retry payment).
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from apps.common.utils import success_response, error_response
from ..models import Order, ReturnOrder
from ..serializers import (
    OrderRefundSerializer, OrderCancelSerializer, OrderPaymentSerializer
)
from ..services import OrderService, RefundService


class CancelOrderView(APIView):
    """Cancel order endpoint matching Node.js /api/order/cancelOrder"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            serializer = OrderCancelSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response("Invalid data", serializer.errors)

            roid = serializer.validated_data['roid']
            
            # Cancel order using service
            success, message = OrderService.cancel_order(request.user, roid)
            
            if success:
                return success_response({}, message)
            else:
                return error_response(message)

        except Exception as e:
            return error_response(f"Server error: {str(e)}")


class RefundOrderView(APIView):
    """Refund order endpoint matching Node.js /api/order/refund"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            serializer = OrderRefundSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response("Invalid refund data", serializer.errors)

            data = serializer.validated_data
            
            # Process refund using service
            success, message = RefundService.process_refund_request(
                request.user, data['roid'], data['rrid'], data['reason']
            )
            
            if success:
                # Get updated order data
                order_data, _ = OrderService.get_order_detail(request.user, data['roid'])
                return success_response({
                    'goods': order_data.get('goods', []) if order_data else [],
                    'isOver': True  # TODO: Calculate if all items are returned
                }, message)
            else:
                return error_response(message)

        except Exception as e:
            return error_response(f"Server error: {str(e)}")


class AgainPayView(APIView):
    """Retry payment endpoint matching Node.js /api/order/againPay"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            serializer = OrderPaymentSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response("Invalid data", serializer.errors)

            roid = serializer.validated_data['roid']
            
            try:
                order = Order.objects.get(roid=roid, uid=request.user)
            except Order.DoesNotExist:
                return error_response("Order not found")

            if order.status != -1:
                return error_response("Order status is invalid")

            # Generate new order ID for retry
            new_roid = OrderService.generate_order_id()
            
            # Update order and return orders with new ID
            with transaction.atomic():
                # Update return orders
                ReturnOrder.objects.filter(roid=roid, uid=request.user).update(roid=new_roid)
                
                # Update order
                order.roid = new_roid
                order.save()

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
                'roid': new_roid
            }, 'Payment retry initiated')

        except Exception as e:
            return error_response(f"Server error: {str(e)}")

