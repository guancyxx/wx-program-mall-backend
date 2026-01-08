from django.db import models
from django.conf import settings


class SystemConfiguration(models.Model):
    """System-wide configuration settings"""
    
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        db_table = 'system_configurations'
        ordering = ['key']
    
    def __str__(self):
        return f"{self.key}: {self.value[:50]}"
    
    @classmethod
    def get_value(cls, key, default=None):
        """Get configuration value by key"""
        try:
            config = cls.objects.get(key=key, is_active=True)
            return config.value
        except cls.DoesNotExist:
            return default
    
    @classmethod
    def set_value(cls, key, value, description='', user=None):
        """Set configuration value"""
        config, created = cls.objects.get_or_create(
            key=key,
            defaults={
                'value': value,
                'description': description,
                'updated_by': user
            }
        )
        
        if not created:
            config.value = value
            config.description = description
            config.updated_by = user
            config.save()
        
        return config

