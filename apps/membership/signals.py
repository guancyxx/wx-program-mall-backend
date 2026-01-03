"""
Signals for membership app
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import MembershipStatus
from .services import MembershipService

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_membership(sender, instance, created, **kwargs):
    """Create membership status when a new user is created"""
    if created:
        try:
            MembershipService.create_membership_for_user(instance)
        except Exception as e:
            # Log the error but don't fail user creation
            print(f"Error creating membership for user {instance.id}: {str(e)}")


@receiver(post_save, sender=User)
def save_user_membership(sender, instance, **kwargs):
    """Ensure membership status exists for existing users"""
    if not hasattr(instance, 'membership') or not instance.membership:
        try:
            MembershipService.create_membership_for_user(instance)
        except Exception as e:
            print(f"Error ensuring membership for user {instance.id}: {str(e)}")