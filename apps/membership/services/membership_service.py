"""
Membership service for tier management and operations.
"""
from django.db import transaction
from decimal import Decimal

from ..models import MembershipStatus, MembershipTier, TierUpgradeLog


class MembershipService:
    """Service class for membership operations"""
    
    @staticmethod
    def create_membership_for_user(user):
        """Create membership status for a new user"""
        return MembershipStatus.create_for_user(user)
    
    @staticmethod
    def update_user_spending(user, amount):
        """Update user's total spending and check for tier upgrades"""
        try:
            membership = user.membership
            membership.update_spending(amount)
            return membership
        except MembershipStatus.DoesNotExist:
            # Create membership if it doesn't exist
            membership = MembershipService.create_membership_for_user(user)
            membership.update_spending(amount)
            return membership
    
    @staticmethod
    def get_user_tier_benefits(user):
        """Get current tier benefits for a user"""
        try:
            return user.membership.get_tier_benefits()
        except MembershipStatus.DoesNotExist:
            # Return Bronze tier benefits as default
            bronze_tier = MembershipTier.get_bronze_tier()
            return bronze_tier.benefits if bronze_tier else {}
    
    @staticmethod
    def calculate_points_multiplier(user):
        """Get points multiplier for user's current tier"""
        try:
            return user.membership.tier.points_multiplier
        except MembershipStatus.DoesNotExist:
            return Decimal('1.0')  # Default Bronze multiplier
    
    @staticmethod
    def calculate_tier_discount(user, order_amount):
        """Calculate tier-based discount for an order"""
        try:
            return user.membership.calculate_tier_discount(order_amount)
        except MembershipStatus.DoesNotExist:
            return Decimal('0')
    
    @staticmethod
    def check_tier_eligibility(user, required_tier_name):
        """Check if user's tier meets the required tier level"""
        try:
            user_tier = user.membership.tier
            required_tier = MembershipTier.objects.filter(name=required_tier_name).first()
            
            if not required_tier:
                return False
            
            return user_tier.min_spending >= required_tier.min_spending
        except MembershipStatus.DoesNotExist:
            return False
    
    @staticmethod
    def get_upgrade_history(user, limit=10):
        """Get user's tier upgrade history"""
        return TierUpgradeLog.objects.filter(user=user).order_by('-created_at')[:limit]
    
    @staticmethod
    def manual_tier_upgrade(user, tier_name, reason="Manual upgrade by admin"):
        """Manually upgrade user to a specific tier"""
        try:
            new_tier = MembershipTier.objects.get(name=tier_name)
            membership = user.membership
            
            with transaction.atomic():
                membership.upgrade_tier(new_tier, reason)
                membership.save()
            
            return membership
        except (MembershipTier.DoesNotExist, MembershipStatus.DoesNotExist) as e:
            raise ValueError(f"Error upgrading tier: {str(e)}")

