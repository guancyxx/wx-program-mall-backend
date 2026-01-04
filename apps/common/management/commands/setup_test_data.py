"""
Management command to set up initial test data.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from apps.membership.models import MembershipTier
from apps.points.models import PointsRule


class Command(BaseCommand):
    help = 'Set up initial test data for development and testing'

    def handle(self, *args, **options):
        """Set up initial data."""
        self.stdout.write('Setting up initial test data...')
        
        with transaction.atomic():
            # Create membership tiers
            self.setup_membership_tiers()
            
            # Create points rules
            self.setup_points_rules()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully set up initial test data')
        )

    def setup_membership_tiers(self):
        """Create membership tiers."""
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
            tier, created = MembershipTier.objects.get_or_create(
                name=tier_data['name'],
                defaults=tier_data
            )
            if created:
                self.stdout.write(f'Created {tier.display_name} tier')
            else:
                self.stdout.write(f'{tier.display_name} tier already exists')

    def setup_points_rules(self):
        """Create points rules."""
        rules_data = [
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
        
        for rule_data in rules_data:
            rule, created = PointsRule.objects.get_or_create(
                rule_type=rule_data['rule_type'],
                defaults=rule_data
            )
            if created:
                self.stdout.write(f'Created {rule.name} rule')
            else:
                self.stdout.write(f'{rule.name} rule already exists')