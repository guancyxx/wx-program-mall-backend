from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
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
        transaction = PointsTransaction.objects.create(
            account=self,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=self.available_points,
            description=description,
            reference_id=reference_id
        )
        
        # Create expiration record (points expire after 12 months)
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


class PointsTransaction(models.Model):
    """Individual points transactions"""
    TRANSACTION_TYPES = [
        ('earning', 'Points Earned'),
        ('redemption', 'Points Redeemed'),
        ('expiration', 'Points Expired'),
        ('adjustment', 'Manual Adjustment'),
        ('refund', 'Refund'),
    ]

    account = models.ForeignKey(PointsAccount, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.IntegerField()  # Positive for earning, negative for spending/expiration
    balance_after = models.IntegerField()  # Account balance after this transaction
    description = models.CharField(max_length=200, blank=True)
    reference_id = models.CharField(max_length=100, blank=True)  # Order ID, etc.
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


class PointsExpiration(models.Model):
    """Track points expiration (12-month expiry)"""
    account = models.ForeignKey(PointsAccount, on_delete=models.CASCADE, related_name='expirations')
    points_amount = models.IntegerField()  # Original points amount
    remaining_points = models.IntegerField()  # Points remaining (after partial redemptions)
    earned_date = models.DateTimeField()
    expiry_date = models.DateTimeField()
    is_expired = models.BooleanField(default=False)
    is_fully_redeemed = models.BooleanField(default=False)
    transaction = models.ForeignKey(PointsTransaction, on_delete=models.CASCADE, null=True, blank=True)
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