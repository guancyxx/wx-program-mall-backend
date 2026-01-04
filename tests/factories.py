"""
Test factories for creating test data using factory_boy.
"""
import factory
from factory.django import DjangoModelFactory
from factory import Faker, SubFactory, LazyAttribute
from decimal import Decimal
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory for creating test users."""
    
    class Meta:
        model = User
        django_get_or_create = ('username',)
    
    username = factory.Sequence(lambda n: f"testuser{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = Faker('first_name')
    last_name = Faker('last_name')
    phone = factory.Sequence(lambda n: f"1234567{n:03d}")
    is_active = True


class MembershipTierFactory(DjangoModelFactory):
    """Factory for creating membership tiers."""
    
    class Meta:
        model = 'membership.MembershipTier'
        django_get_or_create = ('name',)
    
    name = 'bronze'
    display_name = 'Bronze'
    min_spending = Decimal('0')
    max_spending = Decimal('999.99')
    points_multiplier = Decimal('1.0')
    benefits = factory.LazyFunction(lambda: {'free_shipping': False})


class BronzeTierFactory(MembershipTierFactory):
    """Factory for Bronze tier."""
    name = 'bronze'
    display_name = 'Bronze'
    min_spending = Decimal('0')
    max_spending = Decimal('999.99')
    points_multiplier = Decimal('1.0')
    benefits = factory.LazyFunction(lambda: {'free_shipping': False})


class SilverTierFactory(MembershipTierFactory):
    """Factory for Silver tier."""
    name = 'silver'
    display_name = 'Silver'
    min_spending = Decimal('1000')
    max_spending = Decimal('4999.99')
    points_multiplier = Decimal('1.2')
    benefits = factory.LazyFunction(lambda: {'free_shipping': True})


class GoldTierFactory(MembershipTierFactory):
    """Factory for Gold tier."""
    name = 'gold'
    display_name = 'Gold'
    min_spending = Decimal('5000')
    max_spending = Decimal('19999.99')
    points_multiplier = Decimal('1.5')
    benefits = factory.LazyFunction(lambda: {'free_shipping': True, 'early_access': True})


class PlatinumTierFactory(MembershipTierFactory):
    """Factory for Platinum tier."""
    name = 'platinum'
    display_name = 'Platinum'
    min_spending = Decimal('20000')
    max_spending = None
    points_multiplier = Decimal('2.0')
    benefits = factory.LazyFunction(lambda: {
        'free_shipping': True, 
        'early_access': True, 
        'priority_support': True
    })


class MembershipStatusFactory(DjangoModelFactory):
    """Factory for creating membership status."""
    
    class Meta:
        model = 'membership.MembershipStatus'
    
    user = SubFactory(UserFactory)
    tier = SubFactory(BronzeTierFactory)
    total_spending = Decimal('0')


class CategoryFactory(DjangoModelFactory):
    """Factory for creating product categories."""
    
    class Meta:
        model = 'products.Category'
        django_get_or_create = ('name',)
    
    name = factory.Sequence(lambda n: f"Category {n}")


class ProductFactory(DjangoModelFactory):
    """Factory for creating products."""
    
    class Meta:
        model = 'products.Product'
    
    gid = factory.Sequence(lambda n: f"product_{n}")
    name = factory.Sequence(lambda n: f"Product {n}")
    description = Faker('text', max_nb_chars=500)
    price = factory.Faker('pydecimal', left_digits=3, right_digits=2, positive=True)
    category = SubFactory(CategoryFactory)
    status = 1  # Active
    inventory = factory.Faker('pyint', min_value=0, max_value=100)


class PointsAccountFactory(DjangoModelFactory):
    """Factory for creating points accounts."""
    
    class Meta:
        model = 'points.PointsAccount'
    
    user = SubFactory(UserFactory)
    total_points = 0
    available_points = 0
    lifetime_earned = 0
    lifetime_redeemed = 0


class PointsRuleFactory(DjangoModelFactory):
    """Factory for creating points rules."""
    
    class Meta:
        model = 'points.PointsRule'
        django_get_or_create = ('rule_type',)
    
    rule_type = 'purchase'
    name = 'Purchase Points'
    description = 'Points earned from purchases'
    points_per_dollar = Decimal('1.0')
    is_active = True


def create_all_membership_tiers():
    """Create all four membership tiers."""
    return {
        'bronze': BronzeTierFactory(),
        'silver': SilverTierFactory(),
        'gold': GoldTierFactory(),
        'platinum': PlatinumTierFactory(),
    }


def create_user_with_membership(tier_name='bronze', total_spending=0):
    """Create a user with membership status."""
    user = UserFactory()
    
    # Ensure tiers exist
    tiers = create_all_membership_tiers()
    tier = tiers[tier_name]
    
    # Create or get membership status
    from apps.membership.models import MembershipStatus
    membership, created = MembershipStatus.objects.get_or_create(
        user=user,
        defaults={
            'tier': tier,
            'total_spending': Decimal(str(total_spending))
        }
    )
    
    if not created:
        membership.tier = tier
        membership.total_spending = Decimal(str(total_spending))
        membership.save()
    
    # Create points account
    PointsAccountFactory(user=user)
    
    return user, membership