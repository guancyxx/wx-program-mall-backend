from django.db import models
from django.conf import settings


class Address(models.Model):
    """User shipping addresses"""
    TYPE_CHOICES = [
        (0, 'Home'),
        (1, 'Company'),
        (2, 'School'),
        (3, 'Other'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses')
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
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
