"""
Admin order management views.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Q
from django.utils import timezone
from datetime import datetime

from apps.common.utils import success_response, error_response
from ..models import Order, ReturnOrder
from ..serializers import OrderSerializer, OrderListSerializer
from ..services import OrderService, RefundService


class AdminGetAllOrderView(APIView):
    """Get all orders for admin - matches /api/admin/getAllOrder"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Get query parameters
            keyword = request.GET.get('keyword', '')
            status_filter = request.GET.get('status')
            page_index = int(request.GET.get('pageIndex', 0))
            page_size = int(request.GET.get('pageSize', 15))
            start_date = request.GET.get('startDate', '')
            end_date = request.GET.get('endDate', '')

            # Build query
            query = Q()

            # Apply keyword search
            if keyword:
                query &= (
                    Q(roid__icontains=keyword) |
                    Q(uid__id__icontains=keyword) |
                    Q(items__gid__icontains=keyword)
                )

            # Apply status filter
            if status_filter is not None and status_filter != '':
                try:
                    status_value = int(status_filter)
                    query &= Q(status=status_value)
                except ValueError:
                    pass

            # Apply date range filter
            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                    start_dt = timezone.make_aware(start_dt)
                    query &= Q(create_time__gte=start_dt)
                except ValueError:
                    pass

            if end_date:
                try:
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                    end_dt = timezone.make_aware(end_dt)
                    # Add one day to include the entire end date
                    end_dt = end_dt + timezone.timedelta(days=1)
                    query &= Q(create_time__lt=end_dt)
                except ValueError:
                    pass

            # Get orders with prefetch for performance
            orders = Order.objects.filter(query).select_related('uid').prefetch_related(
                'items', 'discounts'
            ).distinct().order_by('-create_time')

            # Apply pagination
            total = orders.count()
            start = page_index * page_size
            end = start + page_size
            page_orders = orders[start:end]

            serializer = OrderListSerializer(page_orders, many=True, context={'request': request})

            # Frontend expects array format, not object with list
            return success_response(serializer.data, 'Orders retrieved successfully')

        except Exception as e:
            return error_response(f"Server error: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminConfirmOrderView(APIView):
    """Admin confirm order (delivery) - matches /api/admin/confirmOrder"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            roid = request.data.get('roid')
            if not roid:
                return error_response("Order ID (roid) is required")

            try:
                order = Order.objects.get(roid=roid)
            except Order.DoesNotExist:
                return error_response("Order not found")

            # Only delivery orders (type=2) can be confirmed
            if order.type != 2:
                return error_response("Only delivery orders can be confirmed")

            # Update order status to completed (3)
            if order.status == 2:  # Shipped
                order.status = 3  # Completed
                order.save()
                return success_response({}, 'Order confirmed successfully')
            else:
                return error_response(f"Order cannot be confirmed in current status: {order.status}")

        except Exception as e:
            return error_response(f"Server error: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminSendGoodsView(APIView):
    """Admin send goods (delivery) - matches /api/admin/sendGoods"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            roid = request.data.get('roid')
            company = request.data.get('company', '')
            number = request.data.get('number', '')
            code = request.data.get('code', '')

            if not roid:
                return error_response("Order ID (roid) is required")

            try:
                order = Order.objects.get(roid=roid)
            except Order.DoesNotExist:
                return error_response("Order not found")

            # Only delivery orders (type=2) can be shipped
            if order.type != 2:
                return error_response("Only delivery orders can be shipped")

            # Update order status to shipped (2)
            if order.status == 1:  # Paid
                order.status = 2  # Shipped
                order.send_time = timezone.now()
                
                # Update logistics info
                if not order.logistics:
                    order.logistics = {}
                order.logistics.update({
                    'company': company,
                    'number': number,
                    'code': code
                })
                
                order.save()
                return success_response({}, 'Goods sent successfully')
            else:
                return error_response(f"Order cannot be shipped in current status: {order.status}")

        except Exception as e:
            return error_response(f"Server error: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminWriteOffOrderView(APIView):
    """Admin write off order (pickup verification) - matches /api/admin/writeOffOrder"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            roid = request.data.get('roid')
            if not roid:
                return error_response("Order ID (roid) is required")

            try:
                order = Order.objects.get(roid=roid)
            except Order.DoesNotExist:
                return error_response("Order not found")

            # Only pickup orders (type=1) can be written off
            if order.type != 1:
                return error_response("Only pickup orders can be written off")

            # Update order status to verified (7)
            if order.status == 1:  # Paid
                order.status = 7  # Verified
                order.verify_time = timezone.now()
                order.verify_status = 1
                order.save()
                return success_response({}, 'Order written off successfully')
            else:
                return error_response(f"Order cannot be written off in current status: {order.status}")

        except Exception as e:
            return error_response(f"Server error: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminRefundView(APIView):
    """Admin refund order - matches /api/admin/adminRefund"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            roid = request.data.get('roid')
            rrid = request.data.get('rrid')
            reason = request.data.get('reason', '管理员退款')

            if not roid:
                return error_response("Order ID (roid) is required")

            try:
                order = Order.objects.get(roid=roid)
            except Order.DoesNotExist:
                return error_response("Order not found")

            # Process refund
            success, message = RefundService.process_admin_refund(
                order, rrid, reason
            )

            if success:
                # Get updated order data
                order_data, _ = OrderService.get_order_detail(order.uid, roid)
                return success_response({
                    'goods': order_data.get('goods', []) if order_data else [],
                    'isOver': order.status == 4  # All items refunded
                }, message)
            else:
                return error_response(message)

        except Exception as e:
            return error_response(f"Server error: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

