from django.db import models


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

