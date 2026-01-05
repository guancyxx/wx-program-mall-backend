from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .services import PointsService

User = get_user_model()


@receiver(post_save, sender=User)
def create_points_account_for_new_user(sender, instance, created, **kwargs):
    """Create points account and award registration points for new users"""
    if created:
        # Create points account
        PointsService.get_or_create_account(instance)
        
        # Award registration points
        PointsService.award_registration_points(instance)