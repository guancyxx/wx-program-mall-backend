from django.db import models


class OrderDiscount(models.Model):
    """Order discounts and promotions for member benefits"""
    
    DISCOUNT_TYPE_CHOICES = [
        ('tier_discount', 'Membership Tier Discount'),
        ('points_redemption', 'Points Redemption'),
        ('free_shipping', 'Free Shipping'),
        ('promotion', 'Promotional Discount'),
    ]
    
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='discounts')
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



