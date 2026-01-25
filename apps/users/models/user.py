from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.common.password_utils import hash_password, verify_password


class User(AbstractUser):
    """Custom User model with WeChat integration and secure password handling"""
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    wechat_openid = models.CharField(max_length=100, unique=True, null=True, blank=True)
    wechat_session_key = models.CharField(max_length=100, null=True, blank=True)
    avatar = models.URLField(max_length=500, null=True, blank=True, help_text="Avatar URL stored in cloud storage")
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
    
    def lock_account(self, duration_minutes=30):
        """
        Lock account for specified duration
        """
        from django.utils import timezone
        from datetime import timedelta
        
        self.account_locked_until = timezone.now() + timedelta(minutes=duration_minutes)
        self.save(update_fields=['account_locked_until'])
    
    def unlock_account(self):
        """
        Unlock account and reset failed login attempts
        """
        self.account_locked_until = None
        self.failed_login_attempts = 0
        self.last_failed_login = None
        self.save(update_fields=['account_locked_until', 'failed_login_attempts', 'last_failed_login'])
    
    def record_failed_login(self):
        """
        Record a failed login attempt and lock account if threshold reached
        """
        from django.utils import timezone
        
        self.failed_login_attempts += 1
        self.last_failed_login = timezone.now()
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.lock_account(duration_minutes=30)
        else:
            self.save(update_fields=['failed_login_attempts', 'last_failed_login'])
    
    def reset_failed_login_attempts(self):
        """
        Reset failed login attempts on successful login
        """
        if self.failed_login_attempts > 0:
            self.failed_login_attempts = 0
            self.last_failed_login = None
            self.save(update_fields=['failed_login_attempts', 'last_failed_login'])








