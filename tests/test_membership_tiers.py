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


class MembershipTierStructureTest(TestCase):
    """Test that all four tiers exist with correct thresholds"""
    
    def setUp(self):
        """Set up test data"""
        # Create the four tiers with correct thresholds
        self.bronze_tier = MembershipTier.objects.create(
            name='bronze',
            display_name='Bronze',
            min_spending=0,
            max_spending=Decimal('999.99'),
            points_multiplier=Decimal('1.0'),
            benefits={'free_shipping': False, 'early_access': False}
        )
        
        self.silver_tier = MembershipTier.objects.create(
            name='silver',
            display_name='Silver',
            min_spending=Decimal('1000'),
            max_spending=Decimal('4999.99'),
            points_multiplier=Decimal('1.2'),
            benefits={'free_shipping': True, 'early_access': False}
        )
        
        self.gold_tier = MembershipTier.objects.create(
            name='gold',
            display_name='Gold',
            min_spending=Decimal('5000'),
            max_spending=Decimal('19999.99'),
            points_multiplier=Decimal('1.5'),
            benefits={'free_shipping': True, 'early_access': True}
        )
        
        self.platinum_tier = MembershipTier.objects.create(
            name='platinum',
            display_name='Platinum',
            min_spending=Decimal('20000'),
            max_spending=None,
            points_multiplier=Decimal('2.0'),
            benefits={'free_shipping': True, 'early_access': True, 'exclusive_products': True}
        )
    
    def test_all_four_tiers_exist(self):
        """Test that all four tiers exist"""
        tier_names = ['bronze', 'silver', 'gold', 'platinum']
        
        for tier_name in tier_names:
            tier = MembershipTier.objects.filter(name=tier_name).first()
            self.assertIsNotNone(tier, f"{tier_name} tier should exist")
    
    def test_bronze_tier_thresholds(self):
        """Test Bronze tier has correct thresholds (0-999)"""
        bronze = MembershipTier.objects.get(name='bronze')
        self.assertEqual(bronze.min_spending, Decimal('0'))
        self.assertEqual(bronze.max_spending, Decimal('999.99'))
        self.assertEqual(bronze.points_multiplier, Decimal('1.0'))
    
    def test_silver_tier_thresholds(self):
        """Test Silver tier has correct thresholds (1000-4999)"""
        silver = MembershipTier.objects.get(name='silver')
        self.assertEqual(silver.min_spending, Decimal('1000'))
        self.assertEqual(silver.max_spending, Decimal('4999.99'))
        self.assertEqual(silver.points_multiplier, Decimal('1.2'))
    
    def test_gold_tier_thresholds(self):
        """Test Gold tier has correct thresholds (5000-19999)"""
        gold = MembershipTier.objects.get(name='gold')
        self.assertEqual(gold.min_spending, Decimal('5000'))
        self.assertEqual(gold.max_spending, Decimal('19999.99'))
        self.assertEqual(gold.points_multiplier, Decimal('1.5'))
    
    def test_platinum_tier_thresholds(self):
        """Test Platinum tier has correct thresholds (20000+)"""
        platinum = MembershipTier.objects.get(name='platinum')
        self.assertEqual(platinum.min_spending, Decimal('20000'))
        self.assertIsNone(platinum.max_spending)  # No upper limit
        self.assertEqual(platinum.points_multiplier, Decimal('2.0'))
    
    def test_tier_ordering(self):
        """Test tiers are ordered by min_spending"""
        tiers = list(MembershipTier.objects.all())
        
        # Should be ordered: Bronze, Silver, Gold, Platinum
        self.assertEqual(tiers[0].name, 'bronze')
        self.assertEqual(tiers[1].name, 'silver')
        self.assertEqual(tiers[2].name, 'gold')
        self.assertEqual(tiers[3].name, 'platinum')
    
    def test_get_tier_for_spending_bronze(self):
        """Test tier selection for Bronze range spending"""
        # Test various amounts in Bronze range
        test_amounts = [0, 100, 500, 999.99]
        
        for amount in test_amounts:
            tier = MembershipTier.get_tier_for_spending(amount)
            self.assertEqual(tier.name, 'bronze', f"Amount {amount} should be Bronze tier")
    
    def test_get_tier_for_spending_silver(self):
        """Test tier selection for Silver range spending"""
        # Test various amounts in Silver range
        test_amounts = [1000, 2500, 4999.99]
        
        for amount in test_amounts:
            tier = MembershipTier.get_tier_for_spending(amount)
            self.assertEqual(tier.name, 'silver', f"Amount {amount} should be Silver tier")
    
    def test_get_tier_for_spending_gold(self):
        """Test tier selection for Gold range spending"""
        # Test various amounts in Gold range
        test_amounts = [5000, 10000, 19999.99]
        
        for amount in test_amounts:
            tier = MembershipTier.get_tier_for_spending(amount)
            self.assertEqual(tier.name, 'gold', f"Amount {amount} should be Gold tier")
    
    def test_get_tier_for_spending_platinum(self):
        """Test tier selection for Platinum range spending"""
        # Test various amounts in Platinum range
        test_amounts = [20000, 50000, 100000]
        
        for amount in test_amounts:
            tier = MembershipTier.get_tier_for_spending(amount)
            self.assertEqual(tier.name, 'platinum', f"Amount {amount} should be Platinum tier")
    
    def test_tier_benefits_structure(self):
        """Test that each tier has the expected benefits structure"""
        bronze = MembershipTier.objects.get(name='bronze')
        silver = MembershipTier.objects.get(name='silver')
        gold = MembershipTier.objects.get(name='gold')
        platinum = MembershipTier.objects.get(name='platinum')
        
        # Bronze should have no premium benefits
        self.assertFalse(bronze.benefits.get('free_shipping', True))
        self.assertFalse(bronze.benefits.get('early_access', True))
        
        # Silver should have free shipping
        self.assertTrue(silver.benefits.get('free_shipping', False))
        self.assertFalse(silver.benefits.get('early_access', True))
        
        # Gold should have free shipping and early access
        self.assertTrue(gold.benefits.get('free_shipping', False))
        self.assertTrue(gold.benefits.get('early_access', False))
        
        # Platinum should have all benefits
        self.assertTrue(platinum.benefits.get('free_shipping', False))
        self.assertTrue(platinum.benefits.get('early_access', False))
        self.assertTrue(platinum.benefits.get('exclusive_products', False))
    
    def test_get_bronze_tier_method(self):
        """Test the get_bronze_tier class method"""
        bronze = MembershipTier.get_bronze_tier()
        self.assertIsNotNone(bronze)
        self.assertEqual(bronze.name, 'bronze')
    
    def test_tier_display_names(self):
        """Test that display names are properly set"""
        tiers = {
            'bronze': 'Bronze',
            'silver': 'Silver', 
            'gold': 'Gold',
            'platinum': 'Platinum'
        }
        
        for name, display_name in tiers.items():
            tier = MembershipTier.objects.get(name=name)
            self.assertEqual(tier.display_name, display_name)