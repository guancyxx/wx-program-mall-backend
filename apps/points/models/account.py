from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class PointsAccount(models.Model):
    """Points account for tracking user's points balance"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='points_account')
    total_points = models.IntegerField(default=0)
    available_points = models.IntegerField(default=0)  # Points available for redemption (excluding expired)
    lifetime_earned = models.IntegerField(default=0)  # Total points ever earned
    lifetime_redeemed = models.IntegerField(default=0)  # Total points ever redeemed
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'points_accounts'
        verbose_name = 'Points Account'
        verbose_name_plural = 'Points Accounts'

    def __str__(self):
        return f"{self.user.username} - {self.available_points} points"

    def add_points(self, amount, transaction_type, description="", reference_id=None):
        """Add points to the account and create transaction record"""
        if amount <= 0:
            raise ValueError("Points amount must be positive")
        
        # Update account balance
        self.total_points += amount
        self.available_points += amount
        self.lifetime_earned += amount
        self.save()
        
        # Create transaction record
        from .transaction import PointsTransaction
        transaction = PointsTransaction.objects.create(
            account=self,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=self.available_points,
            description=description,
            reference_id=reference_id
        )
        
        # Create expiration record (points expire after 12 months)
        from .expiration import PointsExpiration
        PointsExpiration.objects.create(
            account=self,
            points_amount=amount,
            earned_date=timezone.now(),
            expiry_date=timezone.now() + timedelta(days=365),
            transaction=transaction
        )
        
        return transaction

    def redeem_points(self, amount, description="", reference_id=None):
        """Redeem points from the account (FIFO - oldest points first)"""
        if amount <= 0:
            raise ValueError("Redemption amount must be positive")
        
        if amount > self.available_points:
            raise ValueError("Insufficient points for redemption")
        
        remaining_to_redeem = amount
        
        # Get unexpired points ordered by expiry date (FIFO)
        from .expiration import PointsExpiration
        unexpired_points = PointsExpiration.objects.filter(
            account=self,
            is_expired=False,
            remaining_points__gt=0
        ).order_by('expiry_date')
        
        # Redeem from oldest points first
        for expiration_record in unexpired_points:
            if remaining_to_redeem <= 0:
                break
                
            points_to_redeem = min(remaining_to_redeem, expiration_record.remaining_points)
            expiration_record.remaining_points -= points_to_redeem
            
            if expiration_record.remaining_points == 0:
                expiration_record.is_fully_redeemed = True
            
            expiration_record.save()
            remaining_to_redeem -= points_to_redeem
        
        # Update account balance
        self.available_points -= amount
        self.lifetime_redeemed += amount
        self.save()
        
        # Create transaction record
        from .transaction import PointsTransaction
        return PointsTransaction.objects.create(
            account=self,
            transaction_type='redemption',
            amount=-amount,  # Negative for redemption
            balance_after=self.available_points,
            description=description,
            reference_id=reference_id
        )

    def expire_points(self):
        """Expire points that are past their expiry date"""
        from .expiration import PointsExpiration
        from .transaction import PointsTransaction
        
        expired_records = PointsExpiration.objects.filter(
            account=self,
            expiry_date__lt=timezone.now(),
            is_expired=False,
            remaining_points__gt=0
        )
        
        total_expired = 0
        for record in expired_records:
            total_expired += record.remaining_points
            record.is_expired = True
            record.save()
            
            # Create expiration transaction
            PointsTransaction.objects.create(
                account=self,
                transaction_type='expiration',
                amount=-record.remaining_points,
                balance_after=self.available_points - record.remaining_points,
                description=f"Points expired from {record.earned_date.date()}",
                reference_id=f"exp_{record.id}"
            )
        
        # Update available points
        if total_expired > 0:
            self.available_points -= total_expired
            self.save()
        
        return total_expired

    @classmethod
    def create_for_user(cls, user):
        """Create points account for a new user"""
        return cls.objects.create(user=user)








