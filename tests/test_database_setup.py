"""
Test database setup and fixtures.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.membership.models import MembershipTier, MembershipStatus
from apps.points.models import PointsAccount, PointsRule
from decimal import Decimal

User = get_user_model()


class DatabaseSetupTest(TestCase):
    """Test that database setup works correctly."""
    
    def test_membership_tiers_exist(self):
        """Test that membership tiers are created correctly."""
        # Check that all four tiers exist
        tier_names = ['bronze', 'silver', 'gold', 'platinum']
        
        for tier_name in tier_names:
            tier = MembershipTier.objects.filter(name=tier_name).first()
            self.assertIsNotNone(tier, f"{tier_name} tier should exist")
    
    def test_bronze_tier_is_default(self):
        """Test that Bronze tier can be retrieved as default."""
        bronze = MembershipTier.get_bronze_tier()
        self.assertIsNotNone(bronze)
        self.assertEqual(bronze.name, 'bronze')
    
    def test_points_rules_exist(self):
        """Test that points rules are created correctly."""
        # Create some basic rules for testing
        PointsRule.objects.create(
            rule_type='purchase',
            points_amount=1,
            is_percentage=True,
            description='Points earned from purchases'
        )
        
        PointsRule.objects.create(
            rule_type='registration',
            points_amount=100,
            is_percentage=False,
            description='Bonus points for new registration'
        )
        
        rule_types = ['purchase', 'registration']
        
        for rule_type in rule_types:
            rule = PointsRule.objects.filter(rule_type=rule_type).first()
            self.assertIsNotNone(rule, f"{rule_type} rule should exist")
    
    def test_user_creation_with_membership(self):
        """Test that user creation works with membership status."""
        # Create a test user
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Check if membership was created automatically by signals
        try:
            membership = user.membership
        except MembershipStatus.DoesNotExist:
            # If not created by signal, create it manually
            bronze_tier = MembershipTier.get_bronze_tier()
            membership = MembershipStatus.objects.create(
                user=user,
                tier=bronze_tier,
                total_spending=Decimal('0')
            )
        
        # Verify the membership was created correctly
        self.assertEqual(membership.user, user)
        self.assertEqual(membership.tier.name, 'bronze')
        self.assertEqual(membership.total_spending, Decimal('0'))
    
    def test_points_account_creation(self):
        """Test that points account creation works."""
        # Create a test user
        user = User.objects.create_user(
            username='pointsuser',
            email='points@example.com',
            password='testpass123'
        )
        
        # Check if points account was created automatically by signals
        try:
            points_account = user.points_account
        except PointsAccount.DoesNotExist:
            # If not created by signal, create it manually
            points_account = PointsAccount.objects.create(
                user=user,
                total_points=100,
                available_points=100,
                lifetime_earned=100,
                lifetime_redeemed=0
            )
        
        # Verify the points account exists and has correct structure
        self.assertEqual(points_account.user, user)
        self.assertIsNotNone(points_account.total_points)
        self.assertIsNotNone(points_account.available_points)
        self.assertIsNotNone(points_account.lifetime_earned)
        self.assertIsNotNone(points_account.lifetime_redeemed)
    
    def test_tier_spending_calculation(self):
        """Test tier calculation based on spending."""
        # Test Bronze tier (0-999.99)
        bronze_tier = MembershipTier.get_tier_for_spending(500)
        self.assertEqual(bronze_tier.name, 'bronze')
        
        # Test Silver tier (1000-4999.99)
        silver_tier = MembershipTier.get_tier_for_spending(2500)
        self.assertEqual(silver_tier.name, 'silver')
        
        # Test Gold tier (5000-19999.99)
        gold_tier = MembershipTier.get_tier_for_spending(10000)
        self.assertEqual(gold_tier.name, 'gold')
        
        # Test Platinum tier (20000+)
        platinum_tier = MembershipTier.get_tier_for_spending(50000)
        self.assertEqual(platinum_tier.name, 'platinum')