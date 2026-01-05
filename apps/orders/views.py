from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from decimal import Decimal

from apps.common.utils import success_response, error_response
from .models import Order, OrderItem, ReturnOrder
from .serializers import (
    OrderSerializer, OrderCreateSerializer, OrderListSerializer,
    OrderRefundSerializer, OrderCancelSerializer, OrderPaymentSerializer
)
from .services import OrderService, RefundService


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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pay_status(request):
    """Check payment status endpoint matching Node.js /api/order/getPayStatus"""
    try:
        roid = request.GET.get('roid')
        if not roid:
            return error_response("Order ID (roid) is required")

        try:
            order = Order.objects.get(roid=roid, uid=request.user)
        except Order.DoesNotExist:
            return error_response("Order not found")

        if order.status == 1:  # Paid
            # TODO: Generate QR code for pickup orders if needed
            if order.type == 1 and not order.qrcode:
                # Generate QR code logic would go here
                pass
            
            return success_response({
                'amount': float(order.amount)
            }, 'Order payment successful')
        else:
            return error_response("Order not paid")

    except Exception as e:
        return error_response(f"Server error: {str(e)}")


@api_view(['POST'])
@permission_classes([])  # No authentication for callback
def payment_callback(request):
    """WeChat Pay callback endpoint matching Node.js /api/order/callback"""
    try:
        # Import payment service
        from apps.payments.services import WeChatPayService
        
        # Process WeChat Pay callback using the new payment system
        result = WeChatPayService.process_payment_callback(request.body)
        
        if result['success']:
            # Return WeChat Pay expected XML response
            from django.http import HttpResponse
            return HttpResponse(
                result['response'],
                content_type='application/xml',
                status=200
            )
        else:
            # Return WeChat Pay error response
            from django.http import HttpResponse
            return HttpResponse(
                result['response'],
                content_type='application/xml',
                status=400
            )

    except Exception as e:
        # Return WeChat Pay error response for any system errors
        from django.http import HttpResponse
        return HttpResponse(
            '<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[System Error]]></return_msg></xml>',
            content_type='application/xml',
            status=500
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def preview_member_benefits(request):
    """Preview member benefits for order before creation"""
    try:
        serializer = OrderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid order data", serializer.errors)

        goods_list = serializer.validated_data['goods']
        
        # Check member access
        has_access, access_msg = OrderService.check_member_exclusive_access(request.user, goods_list)
        if not has_access:
            return error_response(access_msg)

        # Get member pricing
        goods_with_pricing = OrderService.get_member_pricing(request.user, goods_list)
        
        # Calculate totals
        original_total = OrderService.calculate_order_total(goods_list)
        member_total = OrderService.calculate_order_total(goods_with_pricing)
        
        # Get user's membership info
        try:
            from apps.membership.models import MembershipStatus
            membership_status = MembershipStatus.objects.select_related('tier').get(user=request.user)
            tier_name = membership_status.tier.name
        except MembershipStatus.DoesNotExist:
            tier_name = 'Bronze'

        # Calculate potential additional discounts
        additional_discounts = []
        
        if tier_name in ['Silver', 'Gold', 'Platinum']:
            discount_rates = {
                'Silver': 0.05,
                'Gold': 0.10,
                'Platinum': 0.15
            }
            tier_discount = member_total * Decimal(str(discount_rates[tier_name]))
            additional_discounts.append({
                'type': 'tier_discount',
                'description': f'{tier_name} member discount ({discount_rates[tier_name] * 100}%)',
                'amount': float(tier_discount)
            })

        # Free shipping benefit
        if tier_name in ['Silver', 'Gold', 'Platinum'] and serializer.validated_data['type'] == 2:
            additional_discounts.append({
                'type': 'free_shipping',
                'description': f'Free shipping for {tier_name} members',
                'amount': 10.00  # Standard shipping cost
            })

        # Calculate final total
        total_discount = sum(discount['amount'] for discount in additional_discounts)
        final_total = float(member_total) - total_discount

        return success_response({
            'tier': tier_name,
            'pricing_preview': {
                'original_total': float(original_total),
                'member_pricing_total': float(member_total),
                'member_pricing_savings': float(original_total - member_total),
                'additional_discounts': additional_discounts,
                'total_discount': total_discount,
                'final_total': max(0, final_total)  # Ensure non-negative
            },
            'goods_with_member_pricing': goods_with_pricing,
            'benefits_summary': {
                'has_member_pricing': float(original_total) > float(member_total),
                'has_tier_discount': tier_name in ['Silver', 'Gold', 'Platinum'],
                'has_free_shipping': tier_name in ['Silver', 'Gold', 'Platinum'] and serializer.validated_data['type'] == 2,
                'total_savings': float(original_total) - final_total
            }
        }, 'Member benefits preview generated')

    except Exception as e:
        return error_response(f"Server error: {str(e)}")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_nearest_store(request):
    """Get nearest store endpoint matching Node.js /api/order/getLive"""
    try:
        latitude = request.GET.get('latitude')
        longitude = request.GET.get('longitude')

        if not latitude or not longitude:
            return error_response("Latitude and longitude parameters are required")

        try:
            lat = float(latitude)
            lng = float(longitude)
            
            # Validate coordinates
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                return error_response("Invalid latitude or longitude format")
                
        except ValueError:
            return error_response("Invalid latitude or longitude format")

        # TODO: Implement store lookup with geospatial queries
        # This would require integration with the Live/Store model
        # For now, return mock data
        mock_store = {
            'lid': 1,
            'name': 'Mock Store',
            'address': 'Mock Address',
            'phone': '123-456-7890',
            'status': 1,
            'location': {
                'type': 'Point',
                'coordinates': [lng, lat]
            },
            'distance': 0.5  # Mock distance in km
        }

        return success_response(mock_store, 'Nearest store retrieved successfully')

    except Exception as e:
        return error_response(f"Server error: {str(e)}")