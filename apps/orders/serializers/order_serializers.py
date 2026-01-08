"""
Order serializers for list, detail, and create operations.
"""
from rest_framework import serializers
from ..models import Order, OrderItem, OrderDiscount


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items"""
    
    class Meta:
        model = OrderItem
        fields = [
            'rrid', 'gid', 'quantity', 'price', 'amount', 
            'is_return', 'product_info'
        ]


class OrderDiscountSerializer(serializers.ModelSerializer):
    """Serializer for order discounts"""
    
    class Meta:
        model = OrderDiscount
        fields = [
            'discount_type', 'discount_amount', 'description', 'discount_details'
        ]


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for orders matching Node.js API format"""
    
    items = OrderItemSerializer(many=True, read_only=True)
    discounts = OrderDiscountSerializer(many=True, read_only=True)
    goods = serializers.SerializerMethodField()  # For Node.js compatibility
    createTime = serializers.SerializerMethodField()
    payTime = serializers.SerializerMethodField()
    sendTime = serializers.SerializerMethodField()
    lockTimeout = serializers.SerializerMethodField()
    cancelText = serializers.CharField(source='cancel_text', read_only=True, allow_null=True)
    orderNo = serializers.CharField(source='roid', read_only=True)
    value = serializers.SerializerMethodField()  # Total quantity of goods
    
    class Meta:
        model = Order
        fields = [
            'roid', 'orderNo', 'uid', 'lid', 'createTime', 'payTime', 
            'sendTime', 'amount', 'status', 'refund_info', 'openid', 'type', 
            'logistics', 'remark', 'address', 'lockTimeout', 'cancelText', 
            'qrcode', 'verify_time', 'verify_status', 'items', 'discounts', 
            'goods', 'value'
        ]
        read_only_fields = ['roid', 'create_time', 'pay_time', 'send_time', 'verify_time']

    def get_createTime(self, obj):
        """Convert create_time to timestamp (milliseconds)"""
        if obj.create_time:
            return int(obj.create_time.timestamp() * 1000)
        return None
    
    def get_payTime(self, obj):
        """Convert pay_time to timestamp (milliseconds)"""
        if obj.pay_time:
            return int(obj.pay_time.timestamp() * 1000)
        return None
    
    def get_sendTime(self, obj):
        """Convert send_time to timestamp (milliseconds)"""
        if obj.send_time:
            return int(obj.send_time.timestamp() * 1000)
        return None
    
    def get_lockTimeout(self, obj):
        """Convert lock_timeout to timestamp (milliseconds) for countdown"""
        if obj.lock_timeout:
            return int(obj.lock_timeout.timestamp() * 1000)
        return None

    def get_value(self, obj):
        """Get total quantity of goods in order"""
        return sum(item.quantity for item in obj.items.all())

    def get_goods(self, obj):
        """Convert order items to goods array format for Node.js compatibility"""
        from django.conf import settings
        goods = []
        for item in obj.items.all():
            product_info = item.product_info or {}
            goods_item = {
                'rrid': item.rrid,
                'gid': item.gid,
                'id': item.gid,  # For compatibility with frontend
                'quantity': item.quantity,
                'price': float(item.price),
                'amount': float(item.amount),
                'isReturn': item.is_return,
                **product_info  # Spread product info (image, name, inventory, etc.)
            }
            
            # Ensure image is a full URL
            if 'image' in goods_item and goods_item['image']:
                image_url = goods_item['image']
                if not image_url.startswith('http'):
                    # Build full URL
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
                except Exception:
                    pass
            
            # Ensure required fields exist
            if 'image' not in goods_item or not goods_item['image']:
                goods_item['image'] = ''
            if 'name' not in goods_item:
                goods_item['name'] = '商品'
            if 'inventory' not in goods_item:
                goods_item['inventory'] = 0
            
            goods.append(goods_item)
        return goods
    
    def to_representation(self, instance):
        """Convert to camelCase format for frontend compatibility"""
        data = super().to_representation(instance)
        # Convert nested fields
        if 'refund_info' in data:
            data['refundInfo'] = data.pop('refund_info')
        if 'verify_time' in data:
            data['verifyTime'] = data.pop('verify_time')
        if 'verify_status' in data:
            data['verifyStatus'] = data.pop('verify_status')
        return data


class OrderListSerializer(serializers.ModelSerializer):
    """Simplified serializer for order list matching Node.js getMyOrder API"""
    
    goods = serializers.SerializerMethodField()
    createTime = serializers.SerializerMethodField()
    payTime = serializers.SerializerMethodField()
    sendTime = serializers.SerializerMethodField()
    lockTimeout = serializers.SerializerMethodField()
    cancelText = serializers.CharField(source='cancel_text', read_only=True, allow_null=True)
    orderNo = serializers.CharField(source='roid', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'roid', 'orderNo', 'uid', 'createTime', 'payTime', 'sendTime',
            'amount', 'status', 'refund_info', 'type', 'logistics',
            'remark', 'address', 'lockTimeout', 'cancelText', 'goods'
        ]

    def get_createTime(self, obj):
        """Convert create_time to timestamp (milliseconds)"""
        if obj.create_time:
            return int(obj.create_time.timestamp() * 1000)
        return None
    
    def get_payTime(self, obj):
        """Convert pay_time to timestamp (milliseconds)"""
        if obj.pay_time:
            return int(obj.pay_time.timestamp() * 1000)
        return None
    
    def get_sendTime(self, obj):
        """Convert send_time to timestamp (milliseconds)"""
        if obj.send_time:
            return int(obj.send_time.timestamp() * 1000)
        return None
    
    def get_lockTimeout(self, obj):
        """Convert lock_timeout to timestamp (milliseconds) for countdown"""
        if obj.lock_timeout:
            return int(obj.lock_timeout.timestamp() * 1000)
        return None

    def get_goods(self, obj):
        """Get simplified goods list for order listing"""
        from django.conf import settings
        
        def ensure_full_url(image_url):
            """Ensure image URL has full http/https prefix"""
            if not image_url:
                return ''
            # If already has http/https, return as is
            if image_url.startswith('http://') or image_url.startswith('https://'):
                return image_url
            # If starts with /, prepend BACKEND_URL
            if image_url.startswith('/'):
                return f"{settings.BACKEND_URL}{image_url}"
            # Otherwise, prepend BACKEND_URL with /
            return f"{settings.BACKEND_URL}/{image_url}"
        
        goods = []
        for item in obj.items.all():
            product_info = item.product_info or {}
            # Ensure image field exists for frontend
            goods_item = {
                'rrid': item.rrid,
                'gid': item.gid,
                'id': item.gid,  # For compatibility
                'quantity': item.quantity,
                'price': float(item.price),
                'isReturn': item.is_return,
                **product_info
            }
            
            # Process image URL - ensure it has full http/https prefix
            if 'image' in goods_item and goods_item['image']:
                # If image exists in product_info, ensure it has full URL
                goods_item['image'] = ensure_full_url(goods_item['image'])
            else:
                # If no image in product_info, try to get from product
                try:
                    from apps.products.models import Product, ProductImage
                    # Try to convert gid to int
                    try:
                        gid_int = int(item.gid) if isinstance(item.gid, str) and item.gid.isdigit() else item.gid
                        product = Product.objects.filter(id=gid_int).prefetch_related('images').first()
                    except (ValueError, TypeError):
                        product = None
                    
                    if product:
                        primary_image = product.images.filter(is_primary=True).first()
                        if primary_image:
                            if primary_image.image_url:
                                goods_item['image'] = ensure_full_url(primary_image.image_url)
                            elif primary_image.image:
                                # Build full URL from image field
                                if hasattr(primary_image.image, 'url'):
                                    image_url = primary_image.image.url
                                    goods_item['image'] = ensure_full_url(image_url)
                        else:
                            # Try to get first image
                            first_image = product.images.first()
                            if first_image:
                                if first_image.image_url:
                                    goods_item['image'] = ensure_full_url(first_image.image_url)
                                elif first_image.image:
                                    if hasattr(first_image.image, 'url'):
                                        image_url = first_image.image.url
                                        goods_item['image'] = ensure_full_url(image_url)
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to get product image for gid {item.gid}: {e}")
            
            # Ensure image is a string, default to empty string if missing
            if 'image' not in goods_item or not goods_item['image']:
                goods_item['image'] = ''
            
            # Ensure name exists
            if 'name' not in goods_item:
                goods_item['name'] = '商品'
            
            goods.append(goods_item)
        return goods
    
    def to_representation(self, instance):
        """Convert to camelCase format for frontend compatibility"""
        data = super().to_representation(instance)
        if 'refund_info' in data:
            data['refundInfo'] = data.pop('refund_info')
        return data


class OrderCreateSerializer(serializers.Serializer):
    """Serializer for creating orders matching Node.js createOrder API"""
    
    address = serializers.JSONField()
    goods = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of goods with gid, quantity, price"
    )
    remark = serializers.CharField(max_length=500, required=False, default='无')
    type = serializers.IntegerField(help_text="1=pickup, 2=delivery")
    lid = serializers.IntegerField(required=False, allow_null=True, help_text="Store ID for pickup")

    def validate_goods(self, value):
        """Validate goods list structure"""
        if not value or len(value) == 0:
            raise serializers.ValidationError("Goods list cannot be empty")
        
        for idx, item in enumerate(value):
            # Check required fields
            if not all(key in item for key in ['gid', 'quantity', 'price']):
                raise serializers.ValidationError(
                    f"Goods item {idx}: Each goods item must have 'gid', 'quantity', and 'price'"
                )
            
            # Convert and validate quantity
            try:
                quantity = int(item['quantity']) if isinstance(item['quantity'], str) else item['quantity']
                if quantity <= 0:
                    raise serializers.ValidationError(f"Goods item {idx}: Quantity must be greater than 0")
                item['quantity'] = quantity
            except (ValueError, TypeError):
                raise serializers.ValidationError(f"Goods item {idx}: Invalid quantity value")
            
            # Convert and validate price
            try:
                price = float(item['price']) if isinstance(item['price'], str) else item['price']
                if price <= 0:
                    raise serializers.ValidationError(f"Goods item {idx}: Price must be greater than 0")
                item['price'] = price
            except (ValueError, TypeError):
                raise serializers.ValidationError(f"Goods item {idx}: Invalid price value")
            
            # Ensure gid is not empty
            if not item['gid']:
                raise serializers.ValidationError(f"Goods item {idx}: gid cannot be empty")
        
        return value

    def validate_type(self, value):
        """Validate order type"""
        if value not in [1, 2]:
            raise serializers.ValidationError("Type must be 1 (pickup) or 2 (delivery)")
        return value

    def validate(self, data):
        """Cross-field validation"""
        if data['type'] == 1 and not data.get('lid'):
            raise serializers.ValidationError("Store ID (lid) is required for pickup orders")
        return data


