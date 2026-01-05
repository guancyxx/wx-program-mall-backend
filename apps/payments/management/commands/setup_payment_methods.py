from django.core.management.base import BaseCommand
from apps.payments.models import PaymentMethod


class Command(BaseCommand):
    help = 'Set up initial payment methods'

    def handle(self, *args, **options):
        """Create initial payment methods"""
        
        payment_methods = [
            {
                'name': 'wechat_pay',
                'display_name': '微信支付',
                'is_active': True,
                'sort_order': 1,
                'config': {
                    'description': 'WeChat Pay integration for mini-program and app payments',
                    'supported_types': ['JSAPI', 'NATIVE', 'APP'],
                    'currency': 'CNY'
                }
            },
            {
                'name': 'alipay',
                'display_name': '支付宝',
                'is_active': False,  # Not implemented yet
                'sort_order': 2,
                'config': {
                    'description': 'Alipay integration (future implementation)',
                    'supported_types': ['JSAPI', 'NATIVE', 'APP'],
                    'currency': 'CNY'
                }
            },
            {
                'name': 'bank_card',
                'display_name': '银行卡支付',
                'is_active': False,  # Not implemented yet
                'sort_order': 3,
                'config': {
                    'description': 'Bank card payment integration (future implementation)',
                    'supported_types': ['WEB', 'APP'],
                    'currency': 'CNY'
                }
            },
            {
                'name': 'balance',
                'display_name': '余额支付',
                'is_active': False,  # Not implemented yet
                'sort_order': 4,
                'config': {
                    'description': 'Account balance payment (future implementation)',
                    'supported_types': ['INTERNAL'],
                    'currency': 'CNY'
                }
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for method_data in payment_methods:
            method, created = PaymentMethod.objects.get_or_create(
                name=method_data['name'],
                defaults=method_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created payment method: {method.display_name}')
                )
            else:
                # Update existing method
                for key, value in method_data.items():
                    if key != 'name':  # Don't update the name
                        setattr(method, key, value)
                method.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated payment method: {method.display_name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Payment methods setup complete. Created: {created_count}, Updated: {updated_count}'
            )
        )