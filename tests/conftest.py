"""
Test configuration for Django mall server.
"""
import pytest
import os
import django
from django.conf import settings
from django.db import transaction
from decimal import Decimal


def pytest_configure():
    """Configure Django settings for testing."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mall_server.settings')
    os.environ.setdefault('ENVIRONMENT', 'test')
    django.setup()


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Set up the test database with initial data."""
    with django_db_blocker.unblock():
        # Import here to avoid Django setup issues
        from apps.membership.models import MembershipTier
        from apps.points.models import PointsRule
        
        # Create membership tiers if they don't exist
        with transaction.atomic():
            tiers_data = [
                {
                    'name': 'bronze',
                    'display_name': 'Bronze',
                    'min_spending': Decimal('0'),
                    'max_spending': Decimal('999.99'),
                    'points_multiplier': Decimal('1.0'),
                    'benefits': {'free_shipping': False}
                },
                {
                    'name': 'silver',
                    'display_name': 'Silver',
                    'min_spending': Decimal('1000'),
                    'max_spending': Decimal('4999.99'),
                    'points_multiplier': Decimal('1.2'),
                    'benefits': {'free_shipping': True}
                },
                {
                    'name': 'gold',
                    'display_name': 'Gold',
                    'min_spending': Decimal('5000'),
                    'max_spending': Decimal('19999.99'),
                    'points_multiplier': Decimal('1.5'),
                    'benefits': {'free_shipping': True, 'early_access': True}
                },
                {
                    'name': 'platinum',
                    'display_name': 'Platinum',
                    'min_spending': Decimal('20000'),
                    'max_spending': None,
                    'points_multiplier': Decimal('2.0'),
                    'benefits': {'free_shipping': True, 'early_access': True, 'priority_support': True}
                }
            ]
            
            for tier_data in tiers_data:
                MembershipTier.objects.get_or_create(
                    name=tier_data['name'],
                    defaults=tier_data
                )
            
            # Create default points rules
            points_rules_data = [
                {
                    'rule_type': 'purchase',
                    'name': 'Purchase Points',
                    'description': 'Points earned from purchases',
                    'points_per_dollar': Decimal('1.0'),
                    'is_active': True
                },
                {
                    'rule_type': 'registration',
                    'name': 'Registration Bonus',
                    'description': 'Bonus points for new registration',
                    'points_per_dollar': Decimal('0'),
                    'fixed_points': 100,
                    'is_active': True
                },
                {
                    'rule_type': 'first_purchase',
                    'name': 'First Purchase Bonus',
                    'description': 'Bonus points for first purchase',
                    'points_per_dollar': Decimal('0'),
                    'fixed_points': 200,
                    'is_active': True
                }
            ]
            
            for rule_data in points_rules_data:
                PointsRule.objects.get_or_create(
                    rule_type=rule_data['rule_type'],
                    defaults=rule_data
                )


@pytest.fixture
def user_factory():
    """Factory for creating test users."""
    from tests.factories import UserFactory
    return UserFactory


@pytest.fixture
def membership_tiers():
    """Get existing membership tiers."""
    from apps.membership.models import MembershipTier
    
    return {
        'bronze': MembershipTier.objects.get(name='bronze'),
        'silver': MembershipTier.objects.get(name='silver'),
        'gold': MembershipTier.objects.get(name='gold'),
        'platinum': MembershipTier.objects.get(name='platinum'),
    }


@pytest.fixture
def bronze_tier():
    """Get Bronze tier."""
    from apps.membership.models import MembershipTier
    return MembershipTier.objects.get(name='bronze')


@pytest.fixture
def silver_tier():
    """Get Silver tier."""
    from apps.membership.models import MembershipTier
    return MembershipTier.objects.get(name='silver')


@pytest.fixture
def gold_tier():
    """Get Gold tier."""
    from apps.membership.models import MembershipTier
    return MembershipTier.objects.get(name='gold')


@pytest.fixture
def platinum_tier():
    """Get Platinum tier."""
    from apps.membership.models import MembershipTier
    return MembershipTier.objects.get(name='platinum')


@pytest.fixture
def test_user():
    """Create a test user with Bronze membership."""
    from tests.factories import create_user_with_membership
    user, membership = create_user_with_membership()
    return user


@pytest.fixture
def silver_user():
    """Create a test user with Silver membership."""
    from tests.factories import create_user_with_membership
    user, membership = create_user_with_membership('silver', 2000)
    return user


@pytest.fixture
def gold_user():
    """Create a test user with Gold membership."""
    from tests.factories import create_user_with_membership
    user, membership = create_user_with_membership('gold', 10000)
    return user


@pytest.fixture
def platinum_user():
    """Create a test user with Platinum membership."""
    from tests.factories import create_user_with_membership
    user, membership = create_user_with_membership('platinum', 50000)
    return user


@pytest.fixture
def sample_product():
    """Create a sample product for testing."""
    from tests.factories import ProductFactory
    return ProductFactory()


@pytest.fixture
def sample_category():
    """Create a sample category for testing."""
    from tests.factories import CategoryFactory
    return CategoryFactory()


@pytest.fixture
def points_rules():
    """Get existing points rules."""
    from apps.points.models import PointsRule
    
    return {
        'purchase': PointsRule.objects.get(rule_type='purchase'),
        'registration': PointsRule.objects.get(rule_type='registration'),
        'first_purchase': PointsRule.objects.get(rule_type='first_purchase'),
    }