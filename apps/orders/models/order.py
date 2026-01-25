"""
Order model for managing customer orders.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class Order(models.Model):
    """
    Order model matching Node.js API structure.
    
    Order status codes:
    - -1: Pending payment (待支付)
    - 1: Paid (已支付)
    - 2: Shipped (已发货)
    - 3: Completed (已完成)
    - 4: Refunded (已退单)
    - 5: Cancelled (已取消)
    - 6: Partial refund (部分退款)
    - 7: Verified (已核销)
    
    Order types:
    - 1: Store pickup (到店自提)
    - 2: Delivery (同城配送)
    """
    
    # Order identification
    roid = models.CharField(
        max_length=50,
        unique=True,
        help_text="Order ID from Node.js"
    )
    
    # User and store information
    uid = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column='uid',
        help_text="User ID"
    )
    lid = models.IntegerField(
        null=True,
        blank=True,
        help_text="Live/Store ID for pickup orders"
    )
    
    # Order amounts and pricing
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Total order amount"
    )
    
    # Order status and type
    status = models.IntegerField(
        default=-1,
        help_text="Order status: -1=pending payment, 1=paid, 2=shipped, 3=completed, 4=refunded, 5=cancelled, 6=partial refund, 7=verified"
    )
    type = models.IntegerField(
        choices=[(1, 'Store Pickup'), (2, 'Delivery')],
        default=2,
        help_text="Order type: 1=pickup, 2=delivery"
    )
    
    # Timestamps
    create_time = models.DateTimeField(
        default=timezone.now,
        help_text="Order creation time"
    )
    pay_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Payment completion time"
    )
    send_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Shipping time"
    )
    lock_timeout = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Payment timeout"
    )
    
    # Payment and refund information
    openid = models.CharField(
        max_length=100,
        default='',
        help_text="WeChat OpenID for refunds"
    )
    refund_info = models.JSONField(
        default=dict,
        help_text="Refund information: reason, applyTime"
    )
    cancel_text = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text="Cancellation reason"
    )
    
    # Delivery information
    address = models.JSONField(
        default=dict,
        help_text="Delivery address information"
    )
    logistics = models.JSONField(
        default=dict,
        help_text="Logistics info: company, number, code"
    )
    
    # Order remarks
    remark = models.TextField(
        blank=True,
        default='',
        help_text="Order remarks"
    )
    
    # Verification (for pickup orders)
    qrcode = models.URLField(
        blank=True,
        default='',
        help_text="QR code for order verification"
    )
    verify_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Verification time"
    )
    verify_status = models.IntegerField(
        default=0,
        help_text="Verification status: 0=not verified, 1=verified"
    )
    
    class Meta:
        db_table = 'orders'
        ordering = ['-create_time']
        indexes = [
            models.Index(fields=['roid']),
            models.Index(fields=['uid']),
            models.Index(fields=['status']),
            models.Index(fields=['type']),
            models.Index(fields=['create_time']),
        ]
    
    def __str__(self):
        return f"Order {self.roid} - {self.get_status_display()}"
    
    def get_status_display(self):
        """Get human-readable status"""
        status_map = {
            -1: '待支付',
            1: '已支付',
            2: '已发货',
            3: '已完成',
            4: '已退单',
            5: '已取消',
            6: '部分退款',
            7: '已核销',
        }
        return status_map.get(self.status, f'状态 {self.status}')
    
    def get_type_display(self):
        """Get human-readable order type"""
        return '到店自提' if self.type == 1 else '同城配送'
    
    def is_pickup_order(self):
        """Check if order is a pickup order"""
        return self.type == 1
    
    def is_delivery_order(self):
        """Check if order is a delivery order"""
        return self.type == 2
    
    def can_be_cancelled(self):
        """Check if order can be cancelled"""
        return self.status == -1
    
    def can_be_refunded(self):
        """Check if order can be refunded"""
        return self.status in [1, 2, 3]
    
    def can_be_verified(self):
        """Check if order can be verified (for pickup orders)"""
        return self.is_pickup_order() and self.status == 1
