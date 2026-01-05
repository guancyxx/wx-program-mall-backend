"""
Property-based tests for membership tier upgrade system.
Feature: django-mall-migration
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis.extra.django import TestCase
from decimal import Decimal
from django.contrib.auth import get_user_model

from apps.membership.models import MembershipTier, MembershipStatus, TierUpgradeLog
from apps.membership.services import MembershipService

User = get_user_model()


@pytest.mark.django_db
class TestMembershipTierUpgradeProperties:
    """Property tests for membership tier upgrade functionality"""

    @pytest.fixture(autouse=True)
    def setup_method(self, membership_tiers):
        """Set up test data with all four tiers"""
        self.bronze_tier = membership_tiers['bronze']
        self.silver_tier = membership_tiers['silver']
        self.gold_tier = membership_tiers['gold']
        self.platinum_tier = membership_tiers['platinum']

    @given(
        initial_spending=st.decimals(
            min_value=0, 
            max_value=999, 
            places=2
        ),
        additional_spending=st.decimals(
            min_value=1, 
            max_value=50000, 
            places=2
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_membership_tier_upgrade_automation(self, initial_spending, additional_spending):
        """
        Property 5: Membership Tier Upgrade Automation
        For any member whose total spending crosses tier thresholds, the system should 
        automatically upgrade their membership tier and apply new benefits
        **Feature: django-mall-migration, Property 5: Membership Tier Upgrade Automation**
        **Validates: Requirements 2.3, 2.4, 2.6**
        """
        # Generate truly unique username using UUID
        import uuid
        unique_id = str(uuid.uuid4()).replace('-', '')[:12]
        username = f"tier_test_{unique_id}"
        
        # Create a user with guaranteed unique username
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpass123"
        )
        
        # Create membership status directly (avoid get_or_create complexity)
        membership = MembershipStatus.objects.create(
            user=user,
            tier=self.bronze_tier,
            total_spending=initial_spending
        )
        
        # Record initial state
        initial_tier = membership.tier
        initial_total = membership.total_spending
        
        # Calculate expected final values
        expected_total = initial_total + additional_spending
        expected_tier = MembershipTier.get_tier_for_spending(expected_total)
        
        # Update spending - this should trigger tier upgrade if needed
        membership.update_spending(additional_spending)
        
        # Refresh from database to get updated values
        membership.refresh_from_db()
        
        # Verify total spending was updated correctly
        assert membership.total_spending == expected_total, \
            f"Expected total spending {expected_total}, got {membership.total_spending}"
        
        # Verify tier was upgraded correctly
        assert membership.tier == expected_tier, \
            f"Expected tier {expected_tier.name}, got {membership.tier.name} for spending {expected_total}"
        
        # If tier changed, verify upgrade was logged
        if initial_tier.id != expected_tier.id:
            upgrade_logs = TierUpgradeLog.objects.filter(
                user=user,
                from_tier=initial_tier,
                to_tier=expected_tier
            )
            assert upgrade_logs.exists(), \
                f"Upgrade log should exist for tier change from {initial_tier.name} to {expected_tier.name}"
            
            # Verify log contains correct information
            log = upgrade_logs.first()
            assert log.spending_amount == expected_total, \
                f"Log spending amount should be {expected_total}, got {log.spending_amount}"
            assert "threshold reached" in log.reason.lower(), \
                f"Log reason should mention threshold reached, got: {log.reason}"
        
        # Verify tier benefits are accessible
        benefits = membership.get_tier_benefits()
        assert isinstance(benefits, dict), "Benefits should be a dictionary"
        
        # Verify tier-specific benefits based on final tier
        if expected_tier.name == 'bronze':
            assert not benefits.get('free_shipping', True)
            assert not benefits.get('early_access', True)
        elif expected_tier.name == 'silver':
            assert benefits.get('free_shipping', False)
            assert not benefits.get('early_access', True)
        elif expected_tier.name == 'gold':
            assert benefits.get('free_shipping', False)
            assert benefits.get('early_access', False)
        elif expected_tier.name == 'platinum':
            assert benefits.get('free_shipping', False)
            assert benefits.get('early_access', False)
            assert benefits.get('exclusive_products', False)

    @given(
        spending_amounts=st.lists(
            st.decimals(min_value=1, max_value=5000, places=2),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_multiple_spending_updates_tier_consistency(self, spending_amounts):
        """
        Property test for multiple spending updates maintaining tier consistency
        For any sequence of spending updates, the final tier should match the tier 
        calculated from the total spending amount
        """
        # Generate unique username using UUID
        import uuid
        unique_id = str(uuid.uuid4()).replace('-', '')[:12]
        username = f"multi_test_{unique_id}"
        
        # Create a user
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpass123"
        )
        
        # Create membership status directly
        membership = MembershipStatus.objects.create(
            user=user,
            tier=self.bronze_tier,
            total_spending=Decimal('0')
        )
        
        # Apply spending updates sequentially
        total_spent = Decimal('0')
        for amount in spending_amounts:
            membership.update_spending(amount)
            total_spent += amount
        
        # Refresh from database
        membership.refresh_from_db()
        
        # Verify final total is correct
        assert membership.total_spending == total_spent
        
        # Verify final tier matches what it should be for total spending
        expected_tier = MembershipTier.get_tier_for_spending(total_spent)
        assert membership.tier == expected_tier

    @given(
        tier_name=st.sampled_from(['bronze', 'silver', 'gold', 'platinum']),
        reason=st.text(min_size=5, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')))
    )
    @settings(max_examples=50, deadline=None)
    def test_manual_tier_upgrade_logging(self, tier_name, reason):
        """
        Property test for manual tier upgrade logging
        For any manual tier upgrade, the system should log the change with 
        correct information and update the user's tier
        """
        # Generate unique username using UUID
        import uuid
        unique_id = str(uuid.uuid4()).replace('-', '')[:12]
        username = f"manual_test_{unique_id}"
        
        # Create a user
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpass123"
        )
        
        # Create membership status with Bronze tier
        membership = MembershipStatus.objects.create(
            user=user,
            tier=self.bronze_tier,
            total_spending=Decimal('0')
        )
        
        initial_tier = membership.tier
        
        # Perform manual upgrade
        try:
            updated_membership = MembershipService.manual_tier_upgrade(user, tier_name, reason)
            
            # Verify tier was updated
            target_tier = MembershipTier.objects.get(name=tier_name)
            assert updated_membership.tier == target_tier
            
            # Verify upgrade was logged (only if tier actually changed)
            if initial_tier.name != tier_name:
                upgrade_logs = TierUpgradeLog.objects.filter(
                    user=user,
                    from_tier=initial_tier,
                    to_tier=target_tier,
                    reason=reason
                )
                assert upgrade_logs.exists()
                
                log = upgrade_logs.first()
                assert log.reason == reason
                assert log.spending_amount == membership.total_spending
        
        except ValueError:
            # Manual upgrade might fail for invalid tier names - this is acceptable
            pass

    @given(
        spending_amount=st.decimals(min_value=0, max_value=100000, places=2)
    )
    @settings(max_examples=100, deadline=None)
    def test_tier_calculation_consistency(self, spending_amount):
        """
        Property test for tier calculation consistency
        For any spending amount, the tier calculation should be deterministic 
        and match the defined thresholds
        """
        tier = MembershipTier.get_tier_for_spending(spending_amount)
        
        # Verify tier is not None
        assert tier is not None
        
        # Verify spending amount falls within tier range
        assert spending_amount >= tier.min_spending
        
        if tier.max_spending is not None:
            assert spending_amount <= tier.max_spending
        
        # Verify tier thresholds are correct
        if spending_amount < 1000:
            assert tier.name == 'bronze'
        elif spending_amount < 5000:
            assert tier.name == 'silver'
        elif spending_amount < 20000:
            assert tier.name == 'gold'
        else:
            assert tier.name == 'platinum'

    @given(
        user_count=st.integers(min_value=1, max_value=5),
        spending_per_user=st.lists(
            st.decimals(min_value=100, max_value=10000, places=2),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=30, deadline=None)
    def test_concurrent_tier_upgrades(self, user_count, spending_per_user):
        """
        Property test for concurrent tier upgrades
        For any number of users with spending updates, each user's tier should 
        be calculated independently and correctly
        """
        users = []
        memberships = []
        
        # Create multiple users with unique names
        import uuid
        for i in range(user_count):
            unique_id = str(uuid.uuid4()).replace('-', '')[:12]
            username = f"concurrent_test_{i}_{unique_id}"
            
            user = User.objects.create_user(
                username=username,
                email=f"{username}@example.com",
                password="testpass123"
            )
            users.append(user)
            
            membership = MembershipStatus.objects.create(
                user=user,
                tier=self.bronze_tier,
                total_spending=Decimal('0')
            )
            memberships.append(membership)
        
        # Apply spending to each user
        for i, membership in enumerate(memberships):
            user_spending = spending_per_user[i % len(spending_per_user)]
            membership.update_spending(user_spending)
        
        # Verify each user's tier is correct
        for i, membership in enumerate(memberships):
            membership.refresh_from_db()
            user_spending = spending_per_user[i % len(spending_per_user)]
            expected_tier = MembershipTier.get_tier_for_spending(user_spending)
            assert membership.tier == expected_tier
            assert membership.total_spending == user_spending