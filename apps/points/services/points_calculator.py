"""
Points calculator for tier-based point calculations.
"""
from ..models import PointsRule


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








