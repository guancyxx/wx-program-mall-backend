from django.db import models


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

