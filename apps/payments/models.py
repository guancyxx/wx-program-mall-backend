from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import uuid


class PaymentMethod(models.Model):
    """Supported payment methods"""
    
    METHOD_CHOICES = [
        ('wechat_pay', 'WeChat Pay'),
        ('alipay', 'Alipay'),
        ('bank_card', 'Bank Card'),
        ('balance', 'Account Balance'),
    ]
    
    name = models.CharField(max_length=50, choices=METHOD_CHOICES, unique=True)
    display_name = models.CharField(max_length=100, help_text="Display name for frontend")
    is_active = models.BooleanField(default=True, help_text="Whether this payment method is available")
    sort_order = models.IntegerField(default=0, help_text="Display order in frontend")
    
    # Configuration for payment method (stored as JSON)
    config = models.JSONField(default=dict, help_text="Payment method configuration")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment_methods'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.display_name


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
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
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


class RefundRequest(models.Model):
    """Refund request processing matching Node.js refund structure"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),           # 待处理
        ('processing', 'Processing'),     # 处理中
        ('success', 'Success'),           # 退款成功
        ('failed', 'Failed'),             # 退款失败
        ('rejected', 'Rejected'),         # 已拒绝
    ]
    
    REFUND_TYPE_CHOICES = [
        ('full', 'Full Refund'),          # 全额退款
        ('partial', 'Partial Refund'),    # 部分退款
    ]
    
    # Refund identifiers
    refund_id = models.CharField(max_length=100, unique=True, help_text="Internal refund ID")
    original_transaction = models.ForeignKey(PaymentTransaction, on_delete=models.CASCADE, related_name='refunds')
    order_id = models.CharField(max_length=50, help_text="Related order ID (roid)")
    return_order_id = models.CharField(max_length=50, blank=True, help_text="Return order ID (rrid)")
    
    # Refund details
    refund_type = models.CharField(max_length=10, choices=REFUND_TYPE_CHOICES, default='full')
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Refund amount")
    refund_reason = models.TextField(help_text="Reason for refund")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # External refund system identifiers
    external_refund_id = models.CharField(max_length=200, blank=True, help_text="External system refund ID")
    
    # Refund flow timestamps
    requested_at = models.DateTimeField(auto_now_add=True, help_text="Refund request time")
    processed_at = models.DateTimeField(null=True, blank=True, help_text="Refund processing time")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="Refund completion time")
    
    # Refund processing data
    refund_data = models.JSONField(default=dict, help_text="Additional refund information")
    
    # Error information
    error_code = models.CharField(max_length=50, blank=True, help_text="Error code if refund failed")
    error_message = models.TextField(blank=True, help_text="Error message if refund failed")
    
    # Admin processing
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='processed_refunds',
        help_text="Admin user who processed the refund"
    )
    admin_notes = models.TextField(blank=True, help_text="Admin notes for refund processing")
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'refund_requests'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['order_id']),
            models.Index(fields=['return_order_id']),
            models.Index(fields=['status']),
            models.Index(fields=['original_transaction']),
            models.Index(fields=['requested_at']),
        ]

    def __str__(self):
        return f"Refund {self.refund_id} - {self.status}"

    def save(self, *args, **kwargs):
        # Generate refund ID if not set
        if not self.refund_id:
            self.refund_id = f"refund_{uuid.uuid4().hex[:16]}"
        
        # Set processed_at when status changes to processing
        if self.status == 'processing' and not self.processed_at:
            self.processed_at = timezone.now()
        
        # Set completed_at when status changes to success
        if self.status == 'success' and not self.completed_at:
            self.completed_at = timezone.now()
        
        super().save(*args, **kwargs)


class WeChatPayment(models.Model):
    """WeChat Pay specific data and configuration"""
    
    # Link to main payment transaction
    payment_transaction = models.OneToOneField(
        PaymentTransaction, 
        on_delete=models.CASCADE, 
        related_name='wechat_payment'
    )
    
    # WeChat Pay specific identifiers
    appid = models.CharField(max_length=100, help_text="WeChat App ID")
    mch_id = models.CharField(max_length=100, help_text="WeChat Merchant ID")
    nonce_str = models.CharField(max_length=32, help_text="Random string for signature")
    
    # WeChat Pay order information
    body = models.CharField(max_length=128, help_text="Product description")
    out_trade_no = models.CharField(max_length=32, help_text="Merchant order number")
    total_fee = models.IntegerField(help_text="Total fee in cents (分)")
    spbill_create_ip = models.GenericIPAddressField(help_text="Client IP address")
    
    # WeChat Pay response data
    prepay_id = models.CharField(max_length=64, blank=True, help_text="WeChat prepay ID")
    code_url = models.URLField(blank=True, help_text="QR code URL for native payment")
    
    # WeChat Pay callback data
    transaction_id = models.CharField(max_length=32, blank=True, help_text="WeChat transaction ID")
    bank_type = models.CharField(max_length=16, blank=True, help_text="Bank type")
    settlement_total_fee = models.IntegerField(null=True, blank=True, help_text="Settlement fee")
    cash_fee = models.IntegerField(null=True, blank=True, help_text="Cash fee")
    
    # Signature verification
    sign = models.CharField(max_length=32, blank=True, help_text="WeChat Pay signature")
    sign_type = models.CharField(max_length=10, default='MD5', help_text="Signature type")
    
    # Additional WeChat Pay data
    wechat_data = models.JSONField(default=dict, help_text="Additional WeChat Pay response data")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wechat_payments'
        indexes = [
            models.Index(fields=['out_trade_no']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['prepay_id']),
        ]

    def __str__(self):
        return f"WeChat Payment {self.out_trade_no}"


class PaymentCallback(models.Model):
    """Payment callback logs for debugging and audit"""
    
    CALLBACK_TYPE_CHOICES = [
        ('payment', 'Payment Callback'),
        ('refund', 'Refund Callback'),
    ]
    
    callback_type = models.CharField(max_length=10, choices=CALLBACK_TYPE_CHOICES)
    payment_method = models.CharField(max_length=50, help_text="Payment method that sent callback")
    
    # Request information
    request_method = models.CharField(max_length=10, help_text="HTTP method (GET/POST)")
    request_path = models.CharField(max_length=200, help_text="Request path")
    request_headers = models.JSONField(default=dict, help_text="Request headers")
    request_body = models.TextField(help_text="Raw request body")
    request_ip = models.GenericIPAddressField(help_text="Client IP address")
    
    # Processing information
    processed = models.BooleanField(default=False, help_text="Whether callback was processed successfully")
    processing_error = models.TextField(blank=True, help_text="Error message if processing failed")
    
    # Related records
    transaction_id = models.CharField(max_length=100, blank=True, help_text="Related transaction ID")
    refund_id = models.CharField(max_length=100, blank=True, help_text="Related refund ID")
    
    # Response information
    response_status = models.IntegerField(help_text="HTTP response status code")
    response_body = models.TextField(help_text="Response body sent back")
    
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payment_callbacks'
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['callback_type']),
            models.Index(fields=['payment_method']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['refund_id']),
            models.Index(fields=['received_at']),
            models.Index(fields=['processed']),
        ]

    def __str__(self):
        return f"Callback {self.callback_type} - {self.received_at}"