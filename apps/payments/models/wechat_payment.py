from django.db import models


class WeChatPayment(models.Model):
    """WeChat Pay specific data and configuration"""
    
    # Link to main payment transaction
    payment_transaction = models.OneToOneField(
        'PaymentTransaction', 
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

