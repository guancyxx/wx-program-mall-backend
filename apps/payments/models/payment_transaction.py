from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class PaymentTransaction(models.Model):
    """Payment transaction records matching Node.js payment structure"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),           # 待支付
        ('processing', 'Processing'),     # 处理中
        ('success', 'Success'),           # 支付成功
        ('failed', 'Failed'),             # 支付失败
        ('cancelled', 'Cancelled'),       # 已取消
        ('refunded', 'Refunded'),         # 已退款
        ('partial_refund', 'Partial Refund'),  # 部分退款
    ]
    
    # Transaction identifiers
    transaction_id = models.CharField(max_length=100, unique=True, help_text="Internal transaction ID")
    order_id = models.CharField(max_length=50, help_text="Related order ID (roid)")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Payment details
    payment_method = models.ForeignKey('PaymentMethod', on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Payment amount")
    currency = models.CharField(max_length=3, default='CNY', help_text="Currency code")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # External payment system identifiers
    external_transaction_id = models.CharField(max_length=200, blank=True, help_text="External payment system transaction ID")
    external_order_id = models.CharField(max_length=200, blank=True, help_text="External payment system order ID")
    
    # WeChat Pay specific fields
    wechat_openid = models.CharField(max_length=100, blank=True, help_text="WeChat user OpenID")
    wechat_prepay_id = models.CharField(max_length=200, blank=True, help_text="WeChat prepay ID")
    
    # Payment flow timestamps
    created_at = models.DateTimeField(auto_now_add=True, help_text="Transaction creation time")
    paid_at = models.DateTimeField(null=True, blank=True, help_text="Payment completion time")
    expired_at = models.DateTimeField(null=True, blank=True, help_text="Payment expiration time")
    
    # Additional payment data (stored as JSON for flexibility)
    payment_data = models.JSONField(default=dict, help_text="Additional payment information")
    
    # Callback and notification data
    callback_data = models.JSONField(default=dict, help_text="Payment callback data from external system")
    callback_received_at = models.DateTimeField(null=True, blank=True, help_text="Callback received time")
    
    # Error information
    error_code = models.CharField(max_length=50, blank=True, help_text="Error code if payment failed")
    error_message = models.TextField(blank=True, help_text="Error message if payment failed")
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment_transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_id']),
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['external_transaction_id']),
            models.Index(fields=['wechat_openid']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Payment {self.transaction_id} - {self.status}"

    def save(self, *args, **kwargs):
        # Generate transaction ID if not set
        if not self.transaction_id:
            self.transaction_id = f"pay_{uuid.uuid4().hex[:16]}"
        
        # Set paid_at when status changes to success
        if self.status == 'success' and not self.paid_at:
            self.paid_at = timezone.now()
        
        # Set expiration time for new pending payments (15 minutes)
        if not self.expired_at and self.status == 'pending':
            self.expired_at = timezone.now() + timezone.timedelta(minutes=15)
        
        super().save(*args, **kwargs)


