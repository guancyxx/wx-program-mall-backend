from django.db import models
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from decimal import Decimal


class MembershipStatus(models.Model):
    """User's current membership status"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='membership')
    tier = models.ForeignKey('MembershipTier', on_delete=models.CASCADE)
    total_spending = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tier_start_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'membership_status'

    def __str__(self):
        return f"{self.user.username} - {self.tier.display_name}"

    def update_spending(self, amount):
        """Update total spending and check for tier upgrade"""
        with transaction.atomic():
            old_tier = self.tier
            self.total_spending += Decimal(str(amount))
            
            # Check if tier upgrade is needed
            from .tier import MembershipTier
            new_tier = MembershipTier.get_tier_for_spending(self.total_spending)
            
            if new_tier and new_tier.id != old_tier.id:
                self.upgrade_tier(new_tier, f"Spending threshold reached: ${self.total_spending}")
            
            self.save()

    def upgrade_tier(self, new_tier, reason="Manual upgrade"):
        """Upgrade user to a new tier and log the change"""
        old_tier = self.tier
        
        # Update the tier
        self.tier = new_tier
        self.tier_start_date = timezone.now()
        
        # Log the upgrade
        from .upgrade_log import TierUpgradeLog
        TierUpgradeLog.objects.create(
            user=self.user,
            from_tier=old_tier,
            to_tier=new_tier,
            reason=reason,
            spending_amount=self.total_spending
        )
        
        # Send notification (placeholder for future implementation)
        self._send_tier_upgrade_notification(old_tier, new_tier)

    def _send_tier_upgrade_notification(self, old_tier, new_tier):
        """Send tier upgrade notification to user"""
        from ..services import TierNotificationService
        TierNotificationService.send_upgrade_notification(self.user, old_tier, new_tier)

    def get_tier_benefits(self):
        """Get current tier benefits"""
        return self.tier.benefits

    def calculate_tier_discount(self, order_amount):
        """Calculate tier-based discount for an order"""
        # This is a placeholder - actual discount logic would depend on business rules
        benefits = self.get_tier_benefits()
        
        # Example: 5% discount for Gold, 10% for Platinum
        if self.tier.name == 'gold':
            return Decimal(str(order_amount)) * Decimal('0.05')
        elif self.tier.name == 'platinum':
            return Decimal(str(order_amount)) * Decimal('0.10')
        
        return Decimal('0')

    @classmethod
    def create_for_user(cls, user):
        """Create membership status for a new user with Bronze tier"""
        from .tier import MembershipTier
        bronze_tier = MembershipTier.get_bronze_tier()
        if not bronze_tier:
            raise ValueError("Bronze tier not found. Please run setup_membership_tiers command.")
        
        return cls.objects.create(
            user=user,
            tier=bronze_tier,
            total_spending=0
        )

