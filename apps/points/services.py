from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import PointsAccount, PointsRule, PointsTransaction


class PointsService:
    """Service for handling points operations"""
    
    @staticmethod
    def get_or_create_account(user):
        """Get or create points account for user"""
        account, created = PointsAccount.objects.get_or_create(
            user=user,
            defaults={'total_points': 0, 'available_points': 0}
        )
        return account
    
    @staticmethod
    def award_registration_points(user):
        """Award points for user registration"""
        rule = PointsRule.get_rule('registration')
        if not rule:
            return None
        
        account = PointsService.get_or_create_account(user)
        return account.add_points(
            amount=rule.points_amount,
            transaction_type='earning',
            description='Registration welcome bonus',
            reference_id=f'reg_{user.id}'
        )
    
    @staticmethod
    def award_first_purchase_points(user, order_id):
        """Award points for first purchase"""
        rule = PointsRule.get_rule('first_purchase')
        if not rule:
            return None
        
        account = PointsService.get_or_create_account(user)
        
        # Check if user has made any previous purchases (this would be their first)
        # This logic would need to be integrated with the orders system
        return account.add_points(
            amount=rule.points_amount,
            transaction_type='earning',
            description='First purchase bonus',
            reference_id=f'first_purchase_{order_id}'
        )
    
    @staticmethod
    def award_purchase_points(user, order_amount, tier_multiplier=1.0, order_id=None):
        """Award points for purchase based on order amount and tier multiplier"""
        rule = PointsRule.get_rule('purchase')
        if not rule:
            return None
        
        account = PointsService.get_or_create_account(user)
        
        # Calculate points based on rule and tier multiplier
        points = rule.calculate_points(base_amount=order_amount, tier_multiplier=tier_multiplier)
        
        if points > 0:
            return account.add_points(
                amount=points,
                transaction_type='earning',
                description=f'Purchase points (${order_amount} × {tier_multiplier}x)',
                reference_id=f'order_{order_id}' if order_id else None
            )
        
        return None
    
    @staticmethod
    def award_review_points(user, product_id):
        """Award points for product review"""
        rule = PointsRule.get_rule('review')
        if not rule:
            return None
        
        account = PointsService.get_or_create_account(user)
        
        # Check if user already reviewed this product (prevent duplicate points)
        existing_transaction = PointsTransaction.objects.filter(
            account=account,
            reference_id=f'review_{product_id}',
            transaction_type='earning'
        ).first()
        
        if existing_transaction:
            return None  # Already awarded points for this review
        
        return account.add_points(
            amount=rule.points_amount,
            transaction_type='earning',
            description='Product review points',
            reference_id=f'review_{product_id}'
        )
    
    @staticmethod
    def redeem_points_for_discount(user, points_amount, order_id=None):
        """Redeem points for order discount"""
        if points_amount < 500:  # Minimum redemption: 500 points
            raise ValueError("Minimum redemption is 500 points")
        
        account = PointsService.get_or_create_account(user)
        
        # Calculate discount amount (100 points = $1)
        discount_amount = Decimal(str(points_amount)) / 100
        
        # Redeem points
        transaction = account.redeem_points(
            amount=points_amount,
            description=f'Redeemed for ${discount_amount} discount',
            reference_id=f'discount_{order_id}' if order_id else None
        )
        
        return {
            'transaction': transaction,
            'discount_amount': discount_amount,
            'points_redeemed': points_amount
        }
    
    @staticmethod
    def calculate_max_redeemable_points(user, order_amount):
        """Calculate maximum points that can be redeemed for an order (max 50% of order value)"""
        account = PointsService.get_or_create_account(user)
        
        # Maximum discount is 50% of order value
        max_discount = Decimal(str(order_amount)) * Decimal('0.5')
        
        # Convert to points (100 points = $1)
        max_points_by_order = int(max_discount * 100)
        
        # Can't redeem more than available points
        max_points = min(max_points_by_order, account.available_points)
        
        # Must meet minimum redemption threshold
        if max_points < 500:
            return 0
        
        return max_points
    
    @staticmethod
    def get_points_summary(user):
        """Get comprehensive points summary for user"""
        account = PointsService.get_or_create_account(user)
        
        # Get expiring points (within 30 days)
        from .models import PointsExpiration
        expiring_points = PointsExpiration.get_expiring_soon(user=user)
        expiring_total = sum(exp.remaining_points for exp in expiring_points)
        
        # Get recent transactions
        recent_transactions = account.transactions.all()[:10]
        
        return {
            'available_points': account.available_points,
            'total_points': account.total_points,
            'lifetime_earned': account.lifetime_earned,
            'lifetime_redeemed': account.lifetime_redeemed,
            'expiring_soon': expiring_total,
            'expiring_records': expiring_points,
            'recent_transactions': recent_transactions
        }
    
    @staticmethod
    def expire_user_points(user):
        """Expire points for a specific user"""
        account = PointsService.get_or_create_account(user)
        return account.expire_points()
    
    @staticmethod
    def expire_all_points():
        """Expire points for all users (batch job)"""
        total_expired = 0
        accounts = PointsAccount.objects.all()
        
        for account in accounts:
            expired = account.expire_points()
            total_expired += expired
        
        return total_expired


class TierPointsCalculator:
    """Calculate points based on membership tier"""
    
    # Tier multipliers as defined in requirements
    TIER_MULTIPLIERS = {
        'bronze': 1.0,
        'silver': 1.2,
        'gold': 1.5,
        'platinum': 2.0
    }
    
    @classmethod
    def get_multiplier(cls, tier_name):
        """Get points multiplier for a tier"""
        return cls.TIER_MULTIPLIERS.get(tier_name.lower(), 1.0)
    
    @classmethod
    def calculate_purchase_points(cls, order_amount, tier_name):
        """Calculate points for purchase based on tier"""
        multiplier = cls.get_multiplier(tier_name)
        rule = PointsRule.get_rule('purchase')
        
        if rule:
            return rule.calculate_points(base_amount=order_amount, tier_multiplier=multiplier)
        
        return 0


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