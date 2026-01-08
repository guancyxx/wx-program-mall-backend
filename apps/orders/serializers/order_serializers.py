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
    
    class Meta:
        model = Order
        fields = [
            'roid', 'uid', 'lid', 'create_time', 'pay_time', 'send_time',
            'amount', 'status', 'refund_info', 'openid', 'type', 'logistics',
            'remark', 'address', 'lock_timeout', 'cancel_text', 'qrcode',
            'verify_time', 'verify_status', 'items', 'discounts', 'goods'
        ]
        read_only_fields = ['roid', 'create_time', 'pay_time', 'send_time', 'verify_time']

    def get_goods(self, obj):
        """Convert order items to goods array format for Node.js compatibility"""
        goods = []
        for item in obj.items.all():
            goods.append({
                'rrid': item.rrid,
                'gid': item.gid,
                'quantity': item.quantity,
                'price': float(item.price),
                'amount': float(item.amount),
                'isReturn': item.is_return,
                **item.product_info  # Spread product info
            })
        return goods


class OrderListSerializer(serializers.ModelSerializer):
    """Simplified serializer for order list matching Node.js getMyOrder API"""
    
    goods = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'roid', 'uid', 'create_time', 'pay_time', 'send_time',
            'amount', 'status', 'refund_info', 'type', 'logistics',
            'remark', 'address', 'lock_timeout', 'cancel_text', 'goods'
        ]

    def get_goods(self, obj):
        """Get simplified goods list for order listing"""
        goods = []
        for item in obj.items.all():
            goods.append({
                'rrid': item.rrid,
                'gid': item.gid,
                'quantity': item.quantity,
                'price': float(item.price),
                'isReturn': item.is_return,
                **item.product_info
            })
        return goods


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
        for item in value:
            if not all(key in item for key in ['gid', 'quantity', 'price']):
                raise serializers.ValidationError(
                    "Each goods item must have 'gid', 'quantity', and 'price'"
                )
            if item['quantity'] <= 0:
                raise serializers.ValidationError("Quantity must be greater than 0")
            if item['price'] <= 0:
                raise serializers.ValidationError("Price must be greater than 0")
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

