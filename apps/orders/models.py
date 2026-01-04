from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


class Order(models.Model):
    """Order model matching Node.js structure"""
    
    # Status choices matching Node.js: -1:未支付 1:已支付 2:已发货 3:已结算/收货 4:已退款 5:已取消/时间到期 6:部分退款 7:已核销
    STATUS_CHOICES = [
        (-1, 'Pending Payment'),  # 未支付
        (1, 'Paid'),             # 已支付
        (2, 'Shipped'),          # 已发货
        (3, 'Delivered'),        # 已结算/收货
        (4, 'Refunded'),         # 已退款
        (5, 'Cancelled'),        # 已取消/时间到期
        (6, 'Partial Refund'),   # 部分退款
        (7, 'Verified'),         # 已核销
    ]
    
    # Type choices: 1是到店自取 2是邮寄方式
    TYPE_CHOICES = [
        (1, 'Store Pickup'),     # 到店自取
        (2, 'Delivery'),         # 邮寄方式
    ]

    # Core fields matching Node.js schema
    roid = models.CharField(max_length=50, unique=True, help_text="Order ID from Node.js")
    uid = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='uid', help_text="User ID")
    lid = models.IntegerField(null=True, blank=True, help_text="Live/Store ID for pickup orders")
    
    # Timestamps matching Node.js
    create_time = models.DateTimeField(default=timezone.now, help_text="Order creation time")
    pay_time = models.DateTimeField(null=True, blank=True, help_text="Payment completion time")
    send_time = models.DateTimeField(null=True, blank=True, help_text="Shipping time")
    
    # Order details
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total order amount")
    status = models.IntegerField(choices=STATUS_CHOICES, default=-1, help_text="Order status")
    
    # Refund information (stored as JSON to match Node.js object structure)
    refund_info = models.JSONField(
        default=dict,
        help_text="Refund information: reason, applyTime"
    )
    
    openid = models.CharField(max_length=100, help_text="WeChat OpenID for refunds")
    type = models.IntegerField(choices=TYPE_CHOICES, default=2, help_text="Order type: 1=pickup, 2=delivery")
    
    # Logistics information (stored as JSON to match Node.js object structure)
    logistics = models.JSONField(
        default=dict,
        help_text="Logistics info: company, number, code"
    )
    
    # Order notes and address
    remark = models.TextField(blank=True, default='', help_text="Order remarks")
    address = models.JSONField(default=dict, help_text="Delivery address information")
    
    # Payment timeout
    lock_timeout = models.DateTimeField(null=True, blank=True, help_text="Payment timeout")
    cancel_text = models.CharField(max_length=200, blank=True, default='', help_text="Cancellation reason")
    
    # QR code for verification (pickup orders)
    qrcode = models.URLField(blank=True, default='', help_text="QR code for order verification")
    verify_time = models.DateTimeField(null=True, blank=True, help_text="Verification time")
    verify_status = models.IntegerField(default=0, help_text="Verification status: 0=not verified, 1=verified")

    class Meta:
        db_table = 'orders'
        ordering = ['-create_time']
        indexes = [
            models.Index(fields=['uid']),
            models.Index(fields=['status']),
            models.Index(fields=['roid']),
            models.Index(fields=['lid']),
            models.Index(fields=['create_time']),
        ]

    def __str__(self):
        return f"Order {self.roid}"

    def save(self, *args, **kwargs):
        # Set pay_time when status changes to paid
        if self.status == 1 and not self.pay_time:
            self.pay_time = timezone.now()
        # Set send_time when status changes to shipped
        elif self.status == 2 and not self.send_time:
            self.send_time = timezone.now()
        # Set verify_time when status changes to verified
        elif self.status == 7 and not self.verify_time:
            self.verify_time = timezone.now()
            self.verify_status = 1
        
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """Order line items - represents individual goods in an order"""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    rrid = models.CharField(max_length=50, unique=True, help_text="Return order ID")
    gid = models.CharField(max_length=50, help_text="Product/Goods ID")
    quantity = models.IntegerField(help_text="Quantity ordered")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Unit price")
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Line total (quantity * price)")
    is_return = models.BooleanField(default=False, help_text="Whether item has been returned")
    
    # Additional product info (stored as JSON to match Node.js flexibility)
    product_info = models.JSONField(default=dict, help_text="Product details snapshot")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_items'
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['gid']),
            models.Index(fields=['rrid']),
        ]

    def __str__(self):
        return f"OrderItem {self.rrid} - {self.gid}"

    def save(self, *args, **kwargs):
        # Calculate amount if not set
        if not self.amount:
            self.amount = self.quantity * self.price
        super().save(*args, **kwargs)


class ReturnOrder(models.Model):
    """Return order model matching Node.js returnOrder schema"""
    
    rrid = models.CharField(max_length=50, unique=True, help_text="Return order ID")
    gid = models.CharField(max_length=50, help_text="Product/Goods ID")
    uid = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='uid')
    roid = models.CharField(max_length=50, help_text="Original order ID")
    
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Return amount")
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Refundable amount")
    
    status = models.IntegerField(default=-1, help_text="Return status: -1=pending, 1=completed")
    create_time = models.DateTimeField(default=timezone.now)
    openid = models.CharField(max_length=100, help_text="WeChat OpenID for refunds")

    class Meta:
        db_table = 'return_orders'
        indexes = [
            models.Index(fields=['uid']),
            models.Index(fields=['gid']),
            models.Index(fields=['status']),
            models.Index(fields=['roid']),
            models.Index(fields=['rrid']),
        ]

    def __str__(self):
        return f"ReturnOrder {self.rrid}"


class OrderDiscount(models.Model):
    """Order discounts and promotions for member benefits"""
    
    DISCOUNT_TYPE_CHOICES = [
        ('tier_discount', 'Membership Tier Discount'),
        ('points_redemption', 'Points Redemption'),
        ('free_shipping', 'Free Shipping'),
        ('promotion', 'Promotional Discount'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='discounts')
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=200, help_text="Discount description")
    
    # Additional discount details (stored as JSON for flexibility)
    discount_details = models.JSONField(default=dict, help_text="Additional discount information")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_discounts'
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['discount_type']),
        ]

    def __str__(self):
        return f"Discount {self.discount_type} - {self.discount_amount}"