from django.db import models
from decimal import Decimal


class PointsRule(models.Model):
    """Rules for earning and spending points"""
    RULE_TYPES = [
        ('purchase', 'Purchase'),
        ('registration', 'Registration'),
        ('first_purchase', 'First Purchase'),
        ('review', 'Product Review'),
        ('referral', 'Referral'),
        ('birthday', 'Birthday Bonus'),
        ('redemption', 'Redemption'),
    ]

    rule_type = models.CharField(max_length=20, choices=RULE_TYPES, unique=True)
    points_amount = models.IntegerField()  # Base points amount
    is_percentage = models.BooleanField(default=False)  # If True, points_amount is percentage of order value
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_points_per_transaction = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'points_rules'
        verbose_name = 'Points Rule'
        verbose_name_plural = 'Points Rules'

    def __str__(self):
        return f"{self.get_rule_type_display()} - {self.points_amount} points"

    def calculate_points(self, base_amount=None, tier_multiplier=1.0):
        """Calculate points based on rule and tier multiplier"""
        if self.is_percentage and base_amount:
            points = int((Decimal(str(base_amount)) * Decimal(str(self.points_amount)) / 100))
        else:
            points = self.points_amount
        
        # Apply tier multiplier
        points = int(points * Decimal(str(tier_multiplier)))
        
        # Apply max points limit if set
        if self.max_points_per_transaction:
            points = min(points, self.max_points_per_transaction)
        
        return points

    @classmethod
    def get_rule(cls, rule_type):
        """Get active rule by type"""
        return cls.objects.filter(rule_type=rule_type, is_active=True).first()


