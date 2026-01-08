"""
Core order service for order creation, query, and cancellation.
"""
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import uuid
from typing import Dict, List, Optional, Tuple

from ..models import Order, OrderItem, ReturnOrder
from apps.users.models import User
from .order_member_service import OrderMemberService
from .order_payment_service import OrderPaymentService


class OrderService:
    """Service class for core order business logic"""

    @staticmethod
    def generate_order_id() -> str:
        """Generate unique order ID matching Node.js format"""
        # For now, use UUID. In production, implement sequence like Node.js
        return f"xx_{uuid.uuid4().hex[:10]}"

    @staticmethod
    def generate_return_id() -> str:
        """Generate unique return order ID"""
        return str(uuid.uuid4())

    @staticmethod
    def calculate_order_total(goods_list: List[Dict]) -> Decimal:
        """Calculate total order amount"""
        total = Decimal('0.00')
        for item in goods_list:
            quantity = Decimal(str(item['quantity']))
            price = Decimal(str(item['price']))
            total += quantity * price
        return total

    @staticmethod
    def validate_order_goods(goods_list: List[Dict]) -> Tuple[bool, str]:
        """Validate goods in order"""
        if not goods_list:
            return False, "Order must contain at least one item"
        
        for item in goods_list:
            # Check required fields
            if not all(key in item for key in ['gid', 'quantity', 'price']):
                return False, "Each item must have gid, quantity, and price"
            
            # Validate values
            if item['quantity'] <= 0:
                return False, "Quantity must be greater than 0"
            if item['price'] <= 0:
                return False, "Price must be greater than 0"
            
            # TODO: Validate product exists and has sufficient inventory
            # This would require integration with products app
        
        return True, ""

    @staticmethod
    @transaction.atomic
    def create_order(user: User, order_data: Dict) -> Tuple[Optional[Order], str]:
        """
        Create new order with items and return orders
        Returns (Order, error_message)
        """
        try:
            # Validate goods
            is_valid, error_msg = OrderService.validate_order_goods(order_data['goods'])
            if not is_valid:
                return None, error_msg

            # Check member-exclusive access
            has_access, access_msg = OrderMemberService.check_member_exclusive_access(user, order_data['goods'])
            if not has_access:
                return None, access_msg

            # Apply member pricing
            goods_with_member_pricing = OrderMemberService.get_member_pricing(user, order_data['goods'])

            # Generate order ID
            roid = OrderService.generate_order_id()
            
            # Calculate total amount with member pricing
            total_amount = OrderService.calculate_order_total(goods_with_member_pricing)
            
            # Set payment timeout (15 minutes from now)
            lock_timeout = timezone.now() + timezone.timedelta(minutes=15)
            
            # Create order
            order = Order.objects.create(
                roid=roid,
                uid=user,
                lid=order_data.get('lid'),
                amount=total_amount,
                status=-1,  # Pending payment
                type=order_data['type'],
                address=order_data['address'],
                remark=order_data.get('remark', '无'),
                lock_timeout=lock_timeout,
                openid=getattr(user, 'wechat_openid', '') or 'test_openid',
                refund_info={'reason': '', 'applyTime': ''},
                logistics={'company': '', 'number': '', 'code': ''}
            )
            
            # Create order items and return orders
            for item in goods_with_member_pricing:
                # Generate return order ID
                rrid = OrderService.generate_return_id()
                
                # Calculate item amount with member pricing
                quantity = Decimal(str(item['quantity']))
                price = Decimal(str(item['price']))  # This is now the member price
                amount = quantity * price
                
                # Store both original and member pricing info
                product_info = item.get('product_info', {})
                product_info.update({
                    'original_price': item.get('original_price', item['price']),
                    'member_price': item['price'],
                    'member_discount': item.get('member_discount', 0),
                    'tier': item.get('tier', 'Bronze')
                })
                
                # Create order item
                OrderItem.objects.create(
                    order=order,
                    rrid=rrid,
                    gid=item['gid'],
                    quantity=item['quantity'],
                    price=price,
                    amount=amount,
                    product_info=product_info
                )
                
                # Create return order for refund tracking
                ReturnOrder.objects.create(
                    rrid=rrid,
                    gid=item['gid'],
                    uid=user,
                    roid=roid,
                    amount=amount,
                    refund_amount=amount,
                    status=-1,  # Pending
                    openid=getattr(user, 'wechat_openid', '') or 'test_openid'
                )
            
            # Apply member benefits (discounts, free shipping, etc.)
            OrderMemberService.apply_member_benefits(order)
            
            # Apply additional member promotions
            OrderMemberService.apply_member_promotions(order)
            
            # Generate QR code for pickup orders
            if order.type == 1:  # Store pickup
                qr_code_url = OrderPaymentService.generate_order_qr_code(order)
                order.qrcode = qr_code_url
                order.save()
            
            # Create payment transaction for the order
            try:
                from apps.payments.services import PaymentService
                payment_result = PaymentService.create_payment(
                    user=user,
                    order=order,
                    payment_method='wechat_pay',  # Default to WeChat Pay
                    notify_url='/api/order/callback'  # Use existing callback endpoint
                )
                
                if payment_result['success']:
                    # Store payment transaction ID in order for reference
                    payment_transaction = payment_result['payment_transaction']
                    # Could store payment_transaction.transaction_id in order if needed
                else:
                    # Log payment creation failure but don't fail order creation
                    print(f"Failed to create payment for order {roid}: {payment_result['message']}")
                    
            except Exception as e:
                # Log payment creation error but don't fail order creation
                print(f"Error creating payment for order {roid}: {e}")
            
            return order, ""
            
        except Exception as e:
            return None, f"Failed to create order: {str(e)}"

    @staticmethod
    def get_user_orders(user: User, filters: Dict) -> List[Order]:
        """Get user's orders with filtering"""
        queryset = Order.objects.filter(uid=user).prefetch_related('items', 'discounts')
        
        # Apply status filter
        if 'status' in filters and filters['status'] != '0':
            queryset = queryset.filter(status=filters['status'])
        
        # Apply keyword search
        if 'keyword' in filters and filters['keyword']:
            keyword = filters['keyword']
            queryset = queryset.filter(roid__icontains=keyword)
        
        # Apply pagination
        page_index = int(filters.get('pageIndex', 0))
        page_size = int(filters.get('pageSize', 10))
        
        start = page_index * page_size
        end = start + page_size
        
        return queryset.order_by('-create_time')[start:end]

    @staticmethod
    @transaction.atomic
    def cancel_order(user: User, roid: str) -> Tuple[bool, str]:
        """Cancel an order"""
        try:
            order = Order.objects.get(roid=roid, uid=user)
            
            if order.status != -1:
                return False, "Order cannot be cancelled in current status"
            
            order.status = 5  # Cancelled
            order.lock_timeout = None
            order.cancel_text = "手动取消订单"
            order.save()
            
            return True, "Order cancelled successfully"
            
        except Order.DoesNotExist:
            return False, "Order not found"
        except Exception as e:
            return False, f"Failed to cancel order: {str(e)}"

    @staticmethod
    def get_order_detail(user: User, roid: str, latitude: str = None, longitude: str = None) -> Tuple[Optional[Dict], str]:
        """Get order detail with all information"""
        try:
            order = Order.objects.select_related('uid').prefetch_related('items', 'discounts').get(
                roid=roid, uid=user
            )
            
            # Build order data
            order_data = {
                'roid': order.roid,
                'uid': order.uid.id,
                'create_time': order.create_time,
                'pay_time': order.pay_time,
                'send_time': order.send_time,
                'amount': float(order.amount),
                'status': order.status,
                'refund_info': order.refund_info,
                'type': order.type,
                'logistics': order.logistics,
                'remark': order.remark,
                'address': order.address,
                'lock_timeout': order.lock_timeout,
                'cancel_text': order.cancel_text,
                'lid': order.lid,
                'qrcode': order.qrcode,
                'verify_time': order.verify_time,
                'verify_status': order.verify_status,
                'goods': []
            }
            
            # Add goods/items
            for item in order.items.all():
                order_data['goods'].append({
                    'rrid': item.rrid,
                    'gid': item.gid,
                    'quantity': item.quantity,
                    'price': float(item.price),
                    'amount': float(item.amount),
                    'isReturn': item.is_return,
                    **item.product_info
                })
            
            # TODO: Add store information and distance calculation if needed
            # This would require integration with the Live/Store model
            
            return order_data, ""
            
        except Order.DoesNotExist:
            return None, "Order not found"
        except Exception as e:
            return None, f"Failed to get order detail: {str(e)}"

