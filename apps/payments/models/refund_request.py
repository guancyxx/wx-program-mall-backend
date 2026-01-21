from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


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
    original_transaction = models.ForeignKey('PaymentTransaction', on_delete=models.CASCADE, related_name='refunds')
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







