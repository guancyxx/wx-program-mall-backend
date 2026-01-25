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
                
                # Get product information from database
                product_info = item.get('product_info', {}).copy()
                
                # Fetch product details from database
                try:
                    from apps.products.models import Product, ProductImage
                    # Try to get product by id (gid might be string or int)
                    gid = item['gid']
                    try:
                        product_id = int(gid) if isinstance(gid, str) and gid.isdigit() else gid
                        product = Product.objects.filter(id=product_id).prefetch_related('images').first()
                        
                        if product:
                            # Add product information to product_info
                            product_info.update({
                                'name': product.name,
                                'inventory': product.inventory,
                                'id': str(product.id),
                                'gid': str(product.id),  # Ensure gid is set
                            })
                            
                            # Get product image with full URL
                            from django.conf import settings
                            
                            def ensure_full_url(image_url):
                                """Ensure image URL has full http/https prefix"""
                                if not image_url:
                                    return ''
                                if image_url.startswith('http://') or image_url.startswith('https://'):
                                    return image_url
                                if image_url.startswith('/'):
                                    return f"{settings.BACKEND_URL}{image_url}"
                                return f"{settings.BACKEND_URL}/{image_url}"
                            
                            primary_image = product.images.filter(is_primary=True).first()
                            if primary_image:
                                if primary_image.image_url:
                                    product_info['image'] = ensure_full_url(primary_image.image_url)
                                elif primary_image.image:
                                    # Get full URL for image
                                    image_url = primary_image.image.url if hasattr(primary_image.image, 'url') else f"{settings.MEDIA_URL}{primary_image.image.name}"
                                    product_info['image'] = ensure_full_url(image_url)
                            else:
                                # Try to get first image
                                first_image = product.images.first()
                                if first_image:
                                    if first_image.image_url:
                                        product_info['image'] = ensure_full_url(first_image.image_url)
                                    elif first_image.image:
                                        image_url = first_image.image.url if hasattr(first_image.image, 'url') else f"{settings.MEDIA_URL}{first_image.image.name}"
                                        product_info['image'] = ensure_full_url(image_url)
                            
                            # If still no image, try to get from existing product_info
                            if 'image' not in product_info or not product_info['image']:
                                existing_image = item.get('image', '')
                                if existing_image:
                                    product_info['image'] = ensure_full_url(existing_image)
                                else:
                                    product_info['image'] = ''
                            
                            # Ensure existing image in product_info has full URL
                            if 'image' in product_info and product_info['image']:
                                product_info['image'] = ensure_full_url(product_info['image'])
                    except (ValueError, TypeError) as e:
                        # If gid conversion fails, use existing product_info
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Failed to convert gid {gid} to int: {e}")
                except Exception as e:
                    # If product fetch fails, use existing product_info
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to fetch product info for gid {item['gid']}: {e}")
                
                # Store both original and member pricing info
                product_info.update({
                    'original_price': item.get('original_price', item['price']),
                    'member_price': item['price'],
                    'member_discount': item.get('member_discount', 0),
                    'tier': item.get('tier', 'Bronze')
                })
                
                # Ensure required fields exist
                if 'image' not in product_info:
                    product_info['image'] = item.get('image', '')
                if 'name' not in product_info:
                    product_info['name'] = item.get('name', '商品')
                if 'inventory' not in product_info:
                    product_info['inventory'] = item.get('inventory', 0)
                
                # Create order item
                OrderItem.objects.create(
                    order=order,
                    rrid=rrid,
                    gid=str(item['gid']),  # Ensure gid is string
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
            
            # Payment transaction will be created in the view layer
            # This allows better error handling and response control
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
            
            # For paid pickup orders, ensure QR code exists
            # Generate QR code if missing for pickup orders that are paid
            if order.type == 1 and order.status == 1 and (not order.qrcode or order.qrcode.strip() == ''):
                from .order_payment_service import OrderPaymentService
                qr_code_url = OrderPaymentService.generate_order_qr_code(order)
                order.qrcode = qr_code_url
                order.save(update_fields=['qrcode'])
            
            # Calculate total quantity
            total_quantity = sum(item.quantity for item in order.items.all())
            
            # Build order data with camelCase field names
            # Convert datetime to timestamp (milliseconds) for frontend compatibility
            def to_timestamp(dt):
                """Convert datetime to timestamp in milliseconds"""
                if dt:
                    return int(dt.timestamp() * 1000)
                return None
            
            order_data = {
                'roid': order.roid,
                'orderNo': order.roid,  # For navigation compatibility
                'uid': order.uid.id,
                'createTime': to_timestamp(order.create_time),
                'payTime': to_timestamp(order.pay_time),
                'sendTime': to_timestamp(order.send_time),
                'amount': float(order.amount),
                'status': order.status,
                'refundInfo': order.refund_info,
                'type': order.type,
                'logistics': order.logistics,
                'remark': order.remark,
                'address': order.address,
                'lockTimeout': to_timestamp(order.lock_timeout),
                'cancelText': order.cancel_text,
                'lid': order.lid,  # Store ID stored in lid field
                'qrcode': order.qrcode if order.qrcode else '',  # QR code for verification
                'verifyTime': to_timestamp(order.verify_time),
                'verifyStatus': order.verify_status,
                'value': total_quantity,  # Total quantity of goods
                'goods': [],
                'storeInfo': {}  # Will be populated if lid exists
            }
            
            # Add store information if lid exists (lid stores the store id)
            if order.lid:
                try:
                    from apps.common.models import Store
                    # lid field in Order model stores the store id
                    store = Store.objects.filter(id=order.lid, status=1).first()
                    if store:
                        # Build absolute URL for store image
                        img_url = store.img
                        if img_url and not (img_url.startswith('http://') or img_url.startswith('https://')):
                            # If relative URL, try to build absolute URL
                            # Note: This is a fallback, ideally should use request.build_absolute_uri
                            from django.conf import settings
                            if hasattr(settings, 'MEDIA_URL') and img_url.startswith(settings.MEDIA_URL):
                                base_url = getattr(settings, 'BASE_URL', '')
                                if base_url:
                                    img_url = f"{base_url.rstrip('/')}{img_url}"
                        
                        store_info = {
                            'id': store.id,  # Store ID
                            'name': store.name,
                            'address': store.address,
                            'detail': store.detail,
                            'phone': store.phone,
                            'startTime': store.start_time,
                            'endTime': store.end_time,
                            'distance': 0,  # Will be calculated if latitude/longitude provided
                            'status': store.status,
                            'img': img_url,  # Store image URL (absolute if possible)
                            'location': store.location,
                            'createTime': store.create_time.isoformat() if store.create_time else '',
                        }
                        
                        # Calculate distance if coordinates provided
                        if latitude and longitude:
                            try:
                                lat = float(latitude)
                                lon = float(longitude)
                                distance = store.calculate_distance(lat, lon)
                                if distance is not None:
                                    store_info['distance'] = distance
                            except (ValueError, TypeError) as e:
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.warning(f"Failed to calculate distance: {e}")
                        
                        order_data['storeInfo'] = store_info
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to fetch store info for id {order.lid}: {e}")
            
            # Add goods/items
            from django.conf import settings
            for item in order.items.all():
                product_info = item.product_info or {}
                goods_item = {
                    'rrid': item.rrid,
                    'gid': item.gid,
                    'id': item.gid,  # For compatibility with frontend
                    'quantity': item.quantity,
                    'price': float(item.price),
                    'amount': float(item.amount),
                    'isReturn': item.is_return,
                    **product_info
                }
                
                # Ensure image is a full URL
                if 'image' in goods_item and goods_item['image']:
                    image_url = goods_item['image']
                    if not image_url.startswith('http'):
                        if image_url.startswith('/'):
                            goods_item['image'] = f"{settings.BACKEND_URL}{image_url}"
                        else:
                            goods_item['image'] = f"{settings.BACKEND_URL}/{image_url}"
                elif 'image' not in goods_item or not goods_item['image']:
                    # Try to get from product
                    try:
                        from apps.products.models import Product, ProductImage
                        try:
                            gid_int = int(item.gid) if isinstance(item.gid, str) and item.gid.isdigit() else item.gid
                            product = Product.objects.filter(id=gid_int).prefetch_related('images').first()
                        except (ValueError, TypeError):
                            product = None
                        
                        if product:
                            primary_image = product.images.filter(is_primary=True).first()
                            if primary_image:
                                if primary_image.image_url:
                                    goods_item['image'] = primary_image.image_url if primary_image.image_url.startswith('http') else f"{settings.BACKEND_URL}{primary_image.image_url}"
                                elif primary_image.image:
                                    image_url = primary_image.image.url if hasattr(primary_image.image, 'url') else ''
                                    if image_url and not image_url.startswith('http'):
                                        goods_item['image'] = f"{settings.BACKEND_URL}{image_url}"
                                    else:
                                        goods_item['image'] = image_url
                            else:
                                first_image = product.images.first()
                                if first_image:
                                    if first_image.image_url:
                                        goods_item['image'] = first_image.image_url if first_image.image_url.startswith('http') else f"{settings.BACKEND_URL}{first_image.image_url}"
                                    elif first_image.image:
                                        image_url = first_image.image.url if hasattr(first_image.image, 'url') else ''
                                        if image_url and not image_url.startswith('http'):
                                            goods_item['image'] = f"{settings.BACKEND_URL}{image_url}"
                                        else:
                                            goods_item['image'] = image_url
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Failed to get product image for gid {item.gid}: {e}")
                
                # Ensure required fields exist
                if 'image' not in goods_item or not goods_item['image']:
                    goods_item['image'] = ''
                if 'name' not in goods_item:
                    goods_item['name'] = '商品'
                if 'inventory' not in goods_item:
                    goods_item['inventory'] = 0
                
                order_data['goods'].append(goods_item)
            
            # If order is not paid, actively query payment status from WeChat Pay
            if order.status != 1:  # Not paid
                try:
                    from apps.payments.services import WeChatPayService
                    # Query payment status from WeChat Pay
                    payment_status = WeChatPayService.query_payment_status(order.roid)
                    if payment_status.get('success') and payment_status.get('paid'):
                        # Payment was successful, refresh order from database to get updated status
                        order.refresh_from_db()
                        # Update order_data with new status
                        order_data['status'] = order.status
                        if order.pay_time:
                            order_data['pay_time'] = order.pay_time
                except Exception as e:
                    # Log error but don't fail the request
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to query payment status for order {roid}: {e}")
            
            # TODO: Add store information and distance calculation if needed
            # This would require integration with the Live/Store model
            
            return order_data, ""
            
        except Order.DoesNotExist:
            return None, "Order not found"
        except Exception as e:
            return None, f"Failed to get order detail: {str(e)}"

