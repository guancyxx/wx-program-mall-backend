from django.db import models
from decimal import Decimal


class MembershipTier(models.Model):
    """Membership tier definitions"""
    TIER_CHOICES = [
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ]

    name = models.CharField(max_length=20, choices=TIER_CHOICES, unique=True)
    display_name = models.CharField(max_length=50)
    min_spending = models.DecimalField(max_digits=10, decimal_places=2)
    max_spending = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    points_multiplier = models.DecimalField(max_digits=3, decimal_places=2, default=1.0)
    benefits = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'membership_tiers'
        ordering = ['min_spending']

    def __str__(self):
        return self.display_name

    @classmethod
    def get_tier_for_spending(cls, total_spending):
        """Get the appropriate tier for a given spending amount"""
        total_spending = Decimal(str(total_spending))
        
        # Find the highest tier that the spending qualifies for
        tier = cls.objects.filter(
            min_spending__lte=total_spending
        ).order_by('-min_spending').first()
        
        if tier and (tier.max_spending is None or total_spending <= tier.max_spending):
            return tier
        
        # Fallback to Bronze tier if no tier found
        return cls.objects.filter(name='bronze').first()

    @classmethod
    def get_bronze_tier(cls):
        """Get the default Bronze tier"""
        return cls.objects.filter(name='bronze').first()

