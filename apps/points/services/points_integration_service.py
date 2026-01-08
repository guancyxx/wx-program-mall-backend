"""
Points integration service for integrating points with other systems.
"""
from decimal import Decimal
from .points_service import PointsService
from .points_calculator import TierPointsCalculator


class PointsIntegrationService:
    """Service for integrating points with other systems (orders, membership)"""
    
    @staticmethod
    def handle_order_completion(user, order_amount, order_id, is_first_purchase=False):
        """Handle points award when order is completed"""
        results = []
        
        # Get user's membership tier for multiplier
        try:
            membership = user.membership
            tier_multiplier = TierPointsCalculator.get_multiplier(membership.tier.name)
        except:
            tier_multiplier = 1.0  # Default to Bronze multiplier
        
        # Award purchase points
        purchase_transaction = PointsService.award_purchase_points(
            user=user,
            order_amount=order_amount,
            tier_multiplier=tier_multiplier,
            order_id=order_id
        )
        if purchase_transaction:
            results.append(purchase_transaction)
        
        # Award first purchase bonus if applicable
        if is_first_purchase:
            first_purchase_transaction = PointsService.award_first_purchase_points(
                user=user,
                order_id=order_id
            )
            if first_purchase_transaction:
                results.append(first_purchase_transaction)
        
        return results
    
    @staticmethod
    def handle_user_registration(user):
        """Handle points award when user registers"""
        return PointsService.award_registration_points(user)
    
    @staticmethod
    def validate_points_redemption(user, points_amount, order_amount):
        """Validate if points redemption is allowed"""
        errors = []
        
        account = PointsService.get_or_create_account(user)
        
        # Check minimum redemption
        if points_amount < 500:
            errors.append("Minimum redemption is 500 points")
        
        # Check available points
        if points_amount > account.available_points:
            errors.append(f"Insufficient points. Available: {account.available_points}")
        
        # Check maximum redemption (50% of order value)
        max_redeemable = PointsService.calculate_max_redeemable_points(user, order_amount)
        if points_amount > max_redeemable:
            errors.append(f"Maximum redeemable points for this order: {max_redeemable}")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'max_redeemable': max_redeemable,
            'discount_amount': Decimal(str(points_amount)) / 100 if len(errors) == 0 else 0
        }

