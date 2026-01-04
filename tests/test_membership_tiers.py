"""
Unit tests for membership tier structure
"""
import pytest
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.membership.models import MembershipTier, MembershipStatus, TierUpgradeLog
from apps.membership.services import MembershipService

User = get_user_model()


@pytest.mark.django_db
class TestMembershipTierStructure:
    """Test that all four tiers exist with correct thresholds"""
    
    def test_all_four_tiers_exist(self, membership_tiers):
        """Test that all four tiers exist"""
        tier_names = ['bronze', 'silver', 'gold', 'platinum']
        
        for tier_name in tier_names:
            assert tier_name in membership_tiers
            assert membership_tiers[tier_name] is not None
    
    def test_bronze_tier_thresholds(self, bronze_tier):
        """Test Bronze tier has correct thresholds (0-999)"""
        assert bronze_tier.min_spending == Decimal('0')
        assert bronze_tier.max_spending == Decimal('999.99')
        assert bronze_tier.points_multiplier == Decimal('1.0')
    
    def test_silver_tier_thresholds(self, silver_tier):
        """Test Silver tier has correct thresholds (1000-4999)"""
        assert silver_tier.min_spending == Decimal('1000')
        assert silver_tier.max_spending == Decimal('4999.99')
        assert silver_tier.points_multiplier == Decimal('1.2')
    
    def test_gold_tier_thresholds(self, gold_tier):
        """Test Gold tier has correct thresholds (5000-19999)"""
        assert gold_tier.min_spending == Decimal('5000')
        assert gold_tier.max_spending == Decimal('19999.99')
        assert gold_tier.points_multiplier == Decimal('1.5')
    
    def test_platinum_tier_thresholds(self, platinum_tier):
        """Test Platinum tier has correct thresholds (20000+)"""
        assert platinum_tier.min_spending == Decimal('20000')
        assert platinum_tier.max_spending is None  # No upper limit
        assert platinum_tier.points_multiplier == Decimal('2.0')
    
    def test_tier_ordering(self, membership_tiers):
        """Test tiers are ordered by min_spending"""
        tiers = list(MembershipTier.objects.all().order_by('min_spending'))
        
        # Should be ordered: Bronze, Silver, Gold, Platinum
        assert tiers[0].name == 'bronze'
        assert tiers[1].name == 'silver'
        assert tiers[2].name == 'gold'
        assert tiers[3].name == 'platinum'
    
    def test_get_tier_for_spending_bronze(self):
        """Test tier selection for Bronze range spending"""
        # Test various amounts in Bronze range
        test_amounts = [0, 100, 500, 999.99]
        
        for amount in test_amounts:
            tier = MembershipTier.get_tier_for_spending(amount)
            assert tier.name == 'bronze', f"Amount {amount} should be Bronze tier"
    
    def test_get_tier_for_spending_silver(self):
        """Test tier selection for Silver range spending"""
        # Test various amounts in Silver range
        test_amounts = [1000, 2500, 4999.99]
        
        for amount in test_amounts:
            tier = MembershipTier.get_tier_for_spending(amount)
            assert tier.name == 'silver', f"Amount {amount} should be Silver tier"
    
    def test_get_tier_for_spending_gold(self):
        """Test tier selection for Gold range spending"""
        # Test various amounts in Gold range
        test_amounts = [5000, 10000, 19999.99]
        
        for amount in test_amounts:
            tier = MembershipTier.get_tier_for_spending(amount)
            assert tier.name == 'gold', f"Amount {amount} should be Gold tier"
    
    def test_get_tier_for_spending_platinum(self):
        """Test tier selection for Platinum range spending"""
        # Test various amounts in Platinum range
        test_amounts = [20000, 50000, 100000]
        
        for amount in test_amounts:
            tier = MembershipTier.get_tier_for_spending(amount)
            assert tier.name == 'platinum', f"Amount {amount} should be Platinum tier"
    
    def test_tier_benefits_structure(self, membership_tiers):
        """Test that each tier has the expected benefits structure"""
        bronze = membership_tiers['bronze']
        silver = membership_tiers['silver']
        gold = membership_tiers['gold']
        platinum = membership_tiers['platinum']
        
        # Bronze should have no premium benefits
        assert not bronze.benefits.get('free_shipping', True)
        assert not bronze.benefits.get('early_access', True)
        
        # Silver should have free shipping
        assert silver.benefits.get('free_shipping', False)
        assert not silver.benefits.get('early_access', True)
        
        # Gold should have free shipping and early access
        assert gold.benefits.get('free_shipping', False)
        assert gold.benefits.get('early_access', False)
        
        # Platinum should have all benefits
        assert platinum.benefits.get('free_shipping', False)
        assert platinum.benefits.get('early_access', False)
        assert platinum.benefits.get('priority_support', False)
    
    def test_get_bronze_tier_method(self):
        """Test the get_bronze_tier class method"""
        bronze = MembershipTier.get_bronze_tier()
        assert bronze is not None
        assert bronze.name == 'bronze'
    
    def test_tier_display_names(self, membership_tiers):
        """Test that display names are properly set"""
        expected_names = {
            'bronze': 'Bronze',
            'silver': 'Silver', 
            'gold': 'Gold',
            'platinum': 'Platinum'
        }
        
        for name, display_name in expected_names.items():
            tier = membership_tiers[name]
            assert tier.display_name == display_name