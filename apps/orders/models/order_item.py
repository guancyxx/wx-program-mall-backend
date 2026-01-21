from django.db import models
from decimal import Decimal


class OrderItem(models.Model):
    """Order line items - represents individual goods in an order"""
    
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='items')
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





