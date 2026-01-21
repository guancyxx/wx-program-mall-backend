from django.db import models
from django.utils import timezone
from datetime import timedelta


class PointsExpiration(models.Model):
    """Track points expiration (12-month expiry)"""
    account = models.ForeignKey('PointsAccount', on_delete=models.CASCADE, related_name='expirations')
    points_amount = models.IntegerField()  # Original points amount
    remaining_points = models.IntegerField()  # Points remaining (after partial redemptions)
    earned_date = models.DateTimeField()
    expiry_date = models.DateTimeField()
    is_expired = models.BooleanField(default=False)
    is_fully_redeemed = models.BooleanField(default=False)
    transaction = models.ForeignKey('PointsTransaction', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'points_expirations'
        ordering = ['expiry_date']
        verbose_name = 'Points Expiration'
        verbose_name_plural = 'Points Expirations'

    def __str__(self):
        return f"{self.account.user.username} - {self.remaining_points}/{self.points_amount} points (expires {self.expiry_date.date()})"

    def save(self, *args, **kwargs):
        # Set remaining_points to points_amount on creation
        if not self.pk:
            self.remaining_points = self.points_amount
        super().save(*args, **kwargs)

    @property
    def is_expiring_soon(self):
        """Check if points are expiring within 30 days"""
        return (self.expiry_date - timezone.now()).days <= 30

    @classmethod
    def get_expiring_soon(cls, user=None):
        """Get points expiring within 30 days"""
        expiry_threshold = timezone.now() + timedelta(days=30)
        queryset = cls.objects.filter(
            expiry_date__lte=expiry_threshold,
            is_expired=False,
            remaining_points__gt=0
        )
        
        if user:
            queryset = queryset.filter(account__user=user)
        
        return queryset







