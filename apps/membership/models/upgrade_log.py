from django.db import models
from django.conf import settings


class TierUpgradeLog(models.Model):
    """History of tier changes"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    from_tier = models.ForeignKey('MembershipTier', on_delete=models.CASCADE, related_name='upgrades_from', null=True)
    to_tier = models.ForeignKey('MembershipTier', on_delete=models.CASCADE, related_name='upgrades_to')
    reason = models.CharField(max_length=200)
    spending_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tier_upgrade_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}: {self.from_tier} -> {self.to_tier}"

