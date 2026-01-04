from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import uuid
from typing import Dict, List, Optional, Tuple

from .models import Order, OrderItem, ReturnOrder, OrderDiscount
from apps.users.models import User
from apps.products.models import Product
from apps.membership.services import MembershipService
from apps.points.services import PointsIntegrationService


class OrderService:
    """Service class for order business logic"""

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
            has_access, access_msg = OrderService.check_member_exclusive_access(user, order_data['goods'])
            if not has_access:
                return None, access_msg

            # Apply member pricing
            goods_with_member_pricing = OrderService.get_member_pricing(user, order_data['goods'])

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
            OrderService.apply_member_benefits(order)
            
            # Apply additional member promotions
            OrderService.apply_member_promotions(order)
            
            # Generate QR code for pickup orders
            if order.type == 1:  # Store pickup
                qr_code_url = OrderService.generate_order_qr_code(order)
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
    @transaction.atomic
    def process_payment_success(roid: str) -> Tuple[bool, str]:
        """Process successful payment for an order"""
        try:
            order = Order.objects.get(roid=roid)
            
            if order.status != -1:
                return False, "Order is not in pending payment status"
            
            # Update order status
            order.status = 1  # Paid
            order.pay_time = timezone.now()
            order.lock_timeout = None
            order.save()
            
            # Award membership points
            try:
                PointsIntegrationService.handle_order_completion(
                    user=order.uid,
                    order_amount=order.amount,
                    order_id=roid,
                    is_first_purchase=False  # TODO: Implement first purchase detection
                )
            except Exception as e:
                # Log error but don't fail the payment processing
                print(f"Failed to award points for order {roid}: {e}")
            
            return True, "Payment processed successfully"
            
        except Order.DoesNotExist:
            return False, "Order not found"
        except Exception as e:
            return False, f"Failed to process payment: {str(e)}"

    @staticmethod
    def apply_member_benefits(order: Order) -> None:
        """Apply membership tier benefits to order"""
        try:
            user = order.uid
            
            # Get user's membership status
            try:
                from apps.membership.models import MembershipStatus
                membership_status = MembershipStatus.objects.select_related('tier').get(user=user)
            except MembershipStatus.DoesNotExist:
                # User has no membership status, skip benefits
                return
            
            tier = membership_status.tier
            tier_name = tier.name
            
            # Apply tier-based discount
            discount_rates = {
                'Silver': Decimal('0.05'),    # 5% discount
                'Gold': Decimal('0.10'),      # 10% discount
                'Platinum': Decimal('0.15'),  # 15% discount
            }
            
            if tier_name in discount_rates:
                discount_percentage = discount_rates[tier_name]
                discount_amount = order.amount * discount_percentage
                
                OrderDiscount.objects.create(
                    order=order,
                    discount_type='tier_discount',
                    discount_amount=discount_amount,
                    description=f'{tier_name} member discount ({discount_percentage * 100}%)',
                    discount_details={
                        'tier': tier_name,
                        'percentage': float(discount_percentage),
                        'original_amount': float(order.amount),
                        'discount_amount': float(discount_amount)
                    }
                )
                
                # Update order amount with discount
                order.amount -= discount_amount
                order.save()
            
            # Apply free shipping for Silver+ members (delivery orders only)
            if tier_name in ['Silver', 'Gold', 'Platinum'] and order.type == 2:
                # Assume standard shipping cost
                shipping_cost = Decimal('10.00')
                
                OrderDiscount.objects.create(
                    order=order,
                    discount_type='free_shipping',
                    discount_amount=shipping_cost,
                    description=f'Free shipping for {tier_name} members',
                    discount_details={
                        'tier': tier_name,
                        'shipping_cost_saved': float(shipping_cost)
                    }
                )
            
            # Early access notification for Gold/Platinum members
            if tier_name in ['Gold', 'Platinum']:
                # This would typically trigger notifications for new products
                # For now, just log the benefit
                OrderDiscount.objects.create(
                    order=order,
                    discount_type='promotion',
                    discount_amount=Decimal('0.00'),
                    description=f'{tier_name} member - Early access to new products',
                    discount_details={
                        'tier': tier_name,
                        'benefit_type': 'early_access'
                    }
                )
                
        except Exception as e:
            # Log error but don't fail order creation
            print(f"Failed to apply member benefits for order {order.roid}: {e}")
            import traceback
            traceback.print_exc()

    @staticmethod
    def get_member_pricing(user: User, goods_list: List[Dict]) -> List[Dict]:
        """Apply member-exclusive pricing to goods"""
        try:
            # Get user's membership status
            try:
                from apps.membership.models import MembershipStatus
                membership_status = MembershipStatus.objects.select_related('tier').get(user=user)
                tier_name = membership_status.tier.name
            except MembershipStatus.DoesNotExist:
                # No membership, return original pricing
                return goods_list
            
            # Apply member pricing
            updated_goods = []
            for item in goods_list:
                updated_item = item.copy()
                
                # Check if product has member-exclusive pricing
                # This would typically come from the product model
                original_price = Decimal(str(item['price']))
                
                # Apply tier-based pricing discounts
                if tier_name == 'Silver':
                    member_price = original_price * Decimal('0.95')  # 5% off
                elif tier_name == 'Gold':
                    member_price = original_price * Decimal('0.90')  # 10% off
                elif tier_name == 'Platinum':
                    member_price = original_price * Decimal('0.85')  # 15% off
                else:
                    member_price = original_price
                
                updated_item['original_price'] = float(original_price)
                updated_item['price'] = float(member_price)
                updated_item['member_discount'] = float(original_price - member_price)
                updated_item['tier'] = tier_name
                
                updated_goods.append(updated_item)
            
            return updated_goods
            
        except Exception as e:
            print(f"Failed to apply member pricing: {e}")
            return goods_list

    @staticmethod
    def check_member_exclusive_access(user: User, goods_list: List[Dict]) -> Tuple[bool, str]:
        """Check if user has access to member-exclusive products"""
        try:
            # Get user's membership status
            try:
                from apps.membership.models import MembershipStatus
                membership_status = MembershipStatus.objects.select_related('tier').get(user=user)
                tier_name = membership_status.tier.name
            except MembershipStatus.DoesNotExist:
                tier_name = 'Bronze'  # Default tier
            
            # Check each product for exclusive access requirements
            for item in goods_list:
                # This would typically check the product model for exclusivity settings
                # For now, simulate some products being exclusive to higher tiers
                gid = item.get('gid', '')
                
                # Mock exclusive product check
                if gid.startswith('exclusive_gold_') and tier_name not in ['Gold', 'Platinum']:
                    return False, f"Product {gid} requires Gold membership or higher"
                elif gid.startswith('exclusive_platinum_') and tier_name != 'Platinum':
                    return False, f"Product {gid} requires Platinum membership"
            
            return True, ""
            
        except Exception as e:
            return False, f"Failed to check member access: {str(e)}"

    @staticmethod
    def apply_member_promotions(order: Order) -> None:
        """Apply member-specific promotions and offers"""
        try:
            user = order.uid
            
            # Get user's membership status
            try:
                from apps.membership.models import MembershipStatus
                membership_status = MembershipStatus.objects.select_related('tier').get(user=user)
                tier_name = membership_status.tier.name
            except MembershipStatus.DoesNotExist:
                return
            
            # Apply minimum order promotions
            if tier_name == 'Gold' and order.amount >= Decimal('100.00'):
                # Gold members get extra 5% off orders over $100
                extra_discount = order.amount * Decimal('0.05')
                OrderDiscount.objects.create(
                    order=order,
                    discount_type='promotion',
                    discount_amount=extra_discount,
                    description='Gold member bonus: 5% off orders over $100',
                    discount_details={
                        'tier': tier_name,
                        'promotion_type': 'minimum_order_bonus',
                        'minimum_amount': 100.00,
                        'bonus_percentage': 5.0
                    }
                )
                order.amount -= extra_discount
                order.save()
            
            elif tier_name == 'Platinum' and order.amount >= Decimal('50.00'):
                # Platinum members get extra 10% off orders over $50
                extra_discount = order.amount * Decimal('0.10')
                OrderDiscount.objects.create(
                    order=order,
                    discount_type='promotion',
                    discount_amount=extra_discount,
                    description='Platinum member bonus: 10% off orders over $50',
                    discount_details={
                        'tier': tier_name,
                        'promotion_type': 'minimum_order_bonus',
                        'minimum_amount': 50.00,
                        'bonus_percentage': 10.0
                    }
                )
                order.amount -= extra_discount
                order.save()
                
        except Exception as e:
            print(f"Failed to apply member promotions for order {order.roid}: {e}")

    @staticmethod
    def generate_order_qr_code(order: Order) -> str:
        """Generate QR code for order verification (pickup orders)"""
        try:
            import qrcode
            from io import BytesIO
            import base64
            from django.conf import settings
            
            # Create QR code data - this should contain order verification info
            qr_data = {
                'roid': order.roid,
                'uid': order.uid.id,
                'amount': float(order.amount),
                'type': order.type,
                'verify_code': f"{order.roid}_{order.uid.id}"
            }
            
            # Convert to string format for QR code
            qr_string = f"ORDER_VERIFY:{order.roid}:{order.uid.id}:{order.amount}"
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_string)
            qr.make(fit=True)
            
            # Create QR code image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64 string
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            # Return data URL
            return f"data:image/png;base64,{img_str}"
            
        except ImportError:
            # If qrcode library is not available, return a placeholder URL
            return f"/api/order/qr/{order.roid}"
        except Exception as e:
            print(f"Failed to generate QR code for order {order.roid}: {e}")
            return f"/api/order/qr/{order.roid}"

    @staticmethod
    def get_order_detail(user: User, roid: str) -> Tuple[Optional[Dict], str]:
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


class RefundService:
    """Service class for refund operations"""

    @staticmethod
    @transaction.atomic
    def process_refund_request(user: User, roid: str, rrid: str, reason: str) -> Tuple[bool, str]:
        """Process refund request for an order item"""
        try:
            # Get order
            order = Order.objects.get(roid=roid, uid=user)
            
            # Check if order supports refund
            if order.status in [-1, 2, 3, 4, 5, 7]:
                return False, "This order does not support refund"
            
            # Get return order
            return_order = ReturnOrder.objects.get(rrid=rrid, uid=user, roid=roid)
            
            if return_order.status != -1:
                return False, "Return order status is invalid"
            
            # TODO: Implement actual WeChat Pay refund API call
            # For now, simulate successful refund
            refund_success = True
            
            if not refund_success:
                return False, "Refund failed"
            
            # Update order status
            order.status = 6  # Partial refund
            return_order.status = 1  # Completed
            
            # Update order item
            order_item = OrderItem.objects.get(rrid=rrid)
            order_item.is_return = True
            order_item.save()
            
            # Check if all items are returned
            all_returned = all(item.is_return for item in order.items.all())
            if all_returned:
                order.status = 4  # Full refund
            
            order.save()
            return_order.save()
            
            return True, "Refund processed successfully"
            
        except Order.DoesNotExist:
            return False, "Order not found"
        except ReturnOrder.DoesNotExist:
            return False, "Return order not found"
        except Exception as e:
            return False, f"Failed to process refund: {str(e)}"