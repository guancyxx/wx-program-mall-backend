from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.common.password_utils import hash_password, verify_password


class User(AbstractUser):
    """Custom User model with WeChat integration and secure password handling"""
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    wechat_openid = models.CharField(max_length=100, unique=True, null=True, blank=True)
    wechat_session_key = models.CharField(max_length=100, null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Security fields
    failed_login_attempts = models.IntegerField(default=0)
    last_failed_login = models.DateTimeField(null=True, blank=True)
    account_locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username or self.phone or f"User {self.id}"
    
    def set_password_secure(self, raw_password):
        """
        Set password using secure bcrypt hashing
        """
        self.password = hash_password(raw_password)
        self._password = raw_password
    
    def check_password_secure(self, raw_password):
        """
        Check password using secure verification (supports legacy hashes)
        """
        return verify_password(raw_password, self.password)
    
    def is_account_locked(self):
        """
        Check if account is currently locked due to failed login attempts
        """
        from django.utils import timezone
        
        if self.account_locked_until and self.account_locked_until > timezone.now():
            return True
        return False
    
    def reset_failed_login_attempts(self):
        """
        Reset failed login attempts counter
        """
        self.failed_login_attempts = 0
        self.last_failed_login = None
        self.account_locked_until = None
        self.save(update_fields=['failed_login_attempts', 'last_failed_login', 'account_locked_until'])
    
    def increment_failed_login_attempts(self):
        """
        Increment failed login attempts and lock account if necessary
        """
        from django.utils import timezone
        from datetime import timedelta
        
        self.failed_login_attempts += 1
        self.last_failed_login = timezone.now()
        
        # Lock account after 5 failed attempts for 15 minutes
        if self.failed_login_attempts >= 5:
            self.account_locked_until = timezone.now() + timedelta(minutes=15)
        
        self.save(update_fields=['failed_login_attempts', 'last_failed_login', 'account_locked_until'])


class Address(models.Model):
    """User shipping addresses"""
    TYPE_CHOICES = [
        (0, 'Home'),
        (1, 'Company'),
        (2, 'School'),
        (3, 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    name = models.CharField(max_length=100)  # Recipient name
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=200)  # General address
    detail = models.CharField(max_length=200)  # Detailed address
    address_type = models.IntegerField(choices=TYPE_CHOICES, default=0)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_addresses'
        verbose_name = 'Address'
        verbose_name_plural = 'Addresses'

    def __str__(self):
        return f"{self.name} - {self.address}"

    def save(self, *args, **kwargs):
        # Ensure only one default address per user
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)