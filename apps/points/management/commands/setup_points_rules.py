from django.core.management.base import BaseCommand
from apps.points.models import PointsRule


class Command(BaseCommand):
    help = 'Set up default points rules for the system'

    def handle(self, *args, **options):
        rules_data = [
            {
                'rule_type': 'purchase',
                'points_amount': 1,  # 1% of purchase amount
                'is_percentage': True,
                'description': 'Earn 1% of purchase amount as points (multiplied by tier)'
            },
            {
                'rule_type': 'registration',
                'points_amount': 100,
                'is_percentage': False,
                'description': 'Welcome bonus for new user registration'
            },
            {
                'rule_type': 'first_purchase',
                'points_amount': 200,
                'is_percentage': False,
                'description': 'Bonus points for first purchase'
            },
            {
                'rule_type': 'review',
                'points_amount': 50,
                'is_percentage': False,
                'max_points_per_transaction': 50,
                'description': 'Points for writing product reviews'
            },
            {
                'rule_type': 'referral',
                'points_amount': 500,
                'is_percentage': False,
                'description': 'Points for successful referrals'
            },
            {
                'rule_type': 'birthday',
                'points_amount': 100,
                'is_percentage': False,
                'description': 'Birthday bonus points'
            },
        ]

        created_count = 0
        updated_count = 0

        for rule_data in rules_data:
            rule, created = PointsRule.objects.get_or_create(
                rule_type=rule_data['rule_type'],
                defaults=rule_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created points rule: {rule.get_rule_type_display()}')
                )
            else:
                # Update existing rule with new data
                for key, value in rule_data.items():
                    if key != 'rule_type':
                        setattr(rule, key, value)
                rule.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated points rule: {rule.get_rule_type_display()}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Points rules setup complete. Created: {created_count}, Updated: {updated_count}'
            )
        )