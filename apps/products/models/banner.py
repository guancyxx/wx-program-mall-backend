from django.db import models


class Banner(models.Model):
    """Home page banner/carousel model"""
    TYPE_CHOICES = [
        (1, '小程序内部'),
        (2, '外部小程序'),
        (3, '外部网站'),
    ]
    
    cover = models.CharField(max_length=500, help_text="Banner image URL")
    title = models.CharField(max_length=200, help_text="Jump link/title")
    type = models.IntegerField(choices=TYPE_CHOICES, default=1, help_text="Jump type: 1=internal, 2=external mini-program, 3=external website")
    order = models.IntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True, help_text="Whether banner is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'banners'
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['is_active', 'order']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Banner {self.id}: {self.title}"

