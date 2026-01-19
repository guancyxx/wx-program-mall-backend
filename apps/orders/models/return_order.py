from django.db import models
from django.conf import settings
from django.utils import timezone


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




