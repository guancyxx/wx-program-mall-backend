"""
Django management command to initialize database with default data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from apps.membership.models import MembershipTier
from apps.users.models import User


class Command(BaseCommand):
    help = 'Initialize database with default data'

    def handle(self, *args, **options):
        self.stdout.write('Initializing database with default data...')
        
        self.create_membership_tiers()
        self.create_admin_user()
        
        self.stdout.write(
            self.style.SUCCESS('Database initialization completed!')
        )

    def create_membership_tiers(self):
        """Create default membership tiers"""
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

        for tier_data in tiers:
            tier, created = MembershipTier.objects.get_or_create(
                name=tier_data['name'],
                defaults=tier_data
            )
            if created:
                self.stdout.write(f"Created membership tier: {tier.display_name}")
            else:
                self.stdout.write(f"Membership tier already exists: {tier.display_name}")

    def create_admin_user(self):
        """Create default admin user"""
        admin_data = {
            'username': 'admin',
            'email': 'admin@example.com',
            'phone': '13800000000',
            'password': make_password('admin123456'),
            'is_staff': True,
            'is_superuser': True,
            'first_name': 'Admin',
            'last_name': 'User'
        }

        user, created = User.objects.get_or_create(
            username='admin',
            defaults=admin_data
        )
        if created:
            self.stdout.write(f"Created admin user: {user.username}")
        else:
            self.stdout.write(f"Admin user already exists: {user.username}")