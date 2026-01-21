from django.db import models


class PointsTransaction(models.Model):
    """Individual points transactions"""
    TRANSACTION_TYPES = [
        ('earning', 'Points Earned'),
        ('redemption', 'Points Redeemed'),
        ('expiration', 'Points Expired'),
        ('adjustment', 'Manual Adjustment'),
        ('refund', 'Refund'),
    ]

    account = models.ForeignKey('PointsAccount', on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.IntegerField()  # Positive for earning, negative for spending/expiration
    balance_after = models.IntegerField()  # Account balance after this transaction
    description = models.CharField(max_length=200, blank=True)
    reference_id = models.CharField(max_length=100, blank=True, null=True)  # Order ID, etc.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'points_transactions'
        ordering = ['-created_at']
        verbose_name = 'Points Transaction'
        verbose_name_plural = 'Points Transactions'

    def __str__(self):
        return f"{self.account.user.username} - {self.amount} points ({self.get_transaction_type_display()})"

    @property
    def is_earning(self):
        """Check if this is an earning transaction"""
        return self.amount > 0

    @property
    def is_spending(self):
        """Check if this is a spending transaction"""
        return self.amount < 0







