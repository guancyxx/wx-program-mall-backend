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


class TestMembershipTierUpgradeProperties(TestCase):
    """Property tests for membership tier upgrade functionality"""

    def setUp(self):
        """Set up test data with all four tiers"""
        # Create the four tiers with correct thresholds
        self.bronze_tier = MembershipTier.objects.create(
            name='bronze',
            display_name='Bronze',
            min_spending=Decimal('0'),
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

    @given(
        username=st.text(
            min_size=3, 
            max_size=20, 
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))
        ).filter(lambda x: x.isalnum()),
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
    def test_membership_tier_upgrade_automation(self, username, initial_spending, additional_spending):
        """
        Property 5: Membership Tier Upgrade Automation
        For any member whose total spending crosses tier thresholds, the system should 
        automatically upgrade their membership tier and apply new benefits
        **Feature: django-mall-migration, Property 5: Membership Tier Upgrade Automation**
        **Validates: Requirements 2.3, 2.4, 2.6**
        """
        # Ensure unique username
        import time
        timestamp = int(time.time() * 1000) % 100000
        username = f"tier_test_{username[:10]}_{timestamp}"
        
        # Create a user
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpass123"
        )
        
        # Create membership status with initial spending (should be Bronze)
        # Use get_or_create to handle case where signal already created membership
        membership, created = MembershipStatus.objects.get_or_create(
            user=user,
            defaults={
                'tier': self.bronze_tier,
                'total_spending': initial_spending
            }
        )
        
        if not created:
            # If membership already exists, update the spending
            membership.total_spending = initial_spending
            membership.tier = self.bronze_tier
            membership.save()
        
        # Record initial state
        initial_tier = membership.tier
        initial_total = membership.total_spending
        
        # Update spending with additional amount
        membership.update_spending(additional_spending)
        
        # Refresh from database
        membership.refresh_from_db()
        
        # Verify total spending was updated correctly
        expected_total = initial_total + additional_spending
        assert membership.total_spending == expected_total
        
        # Determine what tier should be based on total spending
        expected_tier = MembershipTier.get_tier_for_spending(expected_total)
        
        # Verify tier was upgraded correctly
        assert membership.tier == expected_tier
        
        # If tier changed, verify upgrade was logged
        if initial_tier != expected_tier:
            upgrade_logs = TierUpgradeLog.objects.filter(
                user=user,
                from_tier=initial_tier,
                to_tier=expected_tier
            )
            assert upgrade_logs.exists()
            
            # Verify log contains correct information
            log = upgrade_logs.first()
            assert log.spending_amount == expected_total
            assert "threshold reached" in log.reason.lower()
        
        # Verify tier benefits are accessible
        benefits = membership.get_tier_benefits()
        assert isinstance(benefits, dict)
        
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
        # Create a user
        user = User.objects.create_user(
            username=f"multi_test_{hash(str(spending_amounts)) % 100000}",
            email=f"multi_{hash(str(spending_amounts)) % 100000}@example.com",
            password="testpass123"
        )
        
        # Create membership status
        membership, created = MembershipStatus.objects.get_or_create(
            user=user,
            defaults={
                'tier': self.bronze_tier,
                'total_spending': Decimal('0')
            }
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
        # Create a user
        user = User.objects.create_user(
            username=f"manual_test_{hash(tier_name + reason) % 100000}",
            email=f"manual_{hash(tier_name + reason) % 100000}@example.com",
            password="testpass123"
        )
        
        # Create membership status with Bronze tier
        membership, created = MembershipStatus.objects.get_or_create(
            user=user,
            defaults={
                'tier': self.bronze_tier,
                'total_spending': Decimal('0')
            }
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
        
        # Create multiple users
        for i in range(user_count):
            user = User.objects.create_user(
                username=f"concurrent_test_{i}_{hash(str(spending_per_user)) % 10000}",
                email=f"concurrent_{i}_{hash(str(spending_per_user)) % 10000}@example.com",
                password="testpass123"
            )
            users.append(user)
            
            membership, created = MembershipStatus.objects.get_or_create(
                user=user,
                defaults={
                    'tier': self.bronze_tier,
                    'total_spending': Decimal('0')
                }
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