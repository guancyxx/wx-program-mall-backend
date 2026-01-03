from django.core.management.base import BaseCommand
from apps.membership.models import MembershipTier


class Command(BaseCommand):
    help = 'Set up initial membership tiers with correct thresholds'

    def handle(self, *args, **options):
        """Create or update membership tiers"""
        tiers = [
            {
                'name': 'bronze',
                'display_name': 'Bronze',
                'min_spending': 0,
                'max_spending': 999.99,
                'points_multiplier': 1.0,
                'benefits': {
                    'free_shipping': False,
                    'early_access': False,
                    'priority_support': False,
                    'exclusive_products': False
                }
            },
            {
                'name': 'silver',
                'display_name': 'Silver',
                'min_spending': 1000,
                'max_spending': 4999.99,
                'points_multiplier': 1.2,
                'benefits': {
                    'free_shipping': True,
                    'early_access': False,
                    'priority_support': False,
                    'exclusive_products': False
                }
            },
            {
                'name': 'gold',
                'display_name': 'Gold',
                'min_spending': 5000,
                'max_spending': 19999.99,
                'points_multiplier': 1.5,
                'benefits': {
                    'free_shipping': True,
                    'early_access': True,
                    'priority_support': True,
                    'exclusive_products': False
                }
            },
            {
                'name': 'platinum',
                'display_name': 'Platinum',
                'min_spending': 20000,
                'max_spending': None,
                'points_multiplier': 2.0,
                'benefits': {
                    'free_shipping': True,
                    'early_access': True,
                    'priority_support': True,
                    'exclusive_products': True
                }
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for tier_data in tiers:
            tier, created = MembershipTier.objects.get_or_create(
                name=tier_data['name'],
                defaults=tier_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created tier: {tier.display_name}')
                )
            else:
                # Update existing tier with new data
                for key, value in tier_data.items():
                    if key != 'name':  # Don't update the name field
                        setattr(tier, key, value)
                tier.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated tier: {tier.display_name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully set up membership tiers: {created_count} created, {updated_count} updated'
            )
        )