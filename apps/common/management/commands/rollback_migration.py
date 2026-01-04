"""
Rollback script for failed data migrations

This script provides rollback capabilities for the MongoDB to Django migration:
1. Backup current Django data before rollback
2. Selective rollback by data type (users, products, orders)
3. Complete rollback of all migrated data
4. Restore from backup functionality

Usage:
    python manage.py rollback_migration --backup-first
    python manage.py rollback_migration --rollback-users
    python manage.py rollback_migration --rollback-all --confirm
"""

import logging
import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core import serializers
from django.conf import settings

# Import Django models
from apps.users.models import Address
from apps.products.models import Product, ProductImage, ProductTag, Category
from apps.orders.models import Order, OrderItem, ReturnOrder, OrderDiscount
from apps.membership.models import MembershipStatus, TierUpgradeLog
from apps.points.models import PointsAccount, PointsTransaction

User = get_user_model()

# Setup logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Rollback data migration from MongoDB to Django'

    def add_arguments(self, parser):
        parser.add_argument(
            '--backup-first',
            action='store_true',
            help='Create backup before rollback'
        )
        parser.add_argument(
            '--rollback-users',
            action='store_true',
            help='Rollback user data only'
        )
        parser.add_argument(
            '--rollback-products',
            action='store_true',
            help='Rollback product data only'
        )
        parser.add_argument(
            '--rollback-orders',
            action='store_true',
            help='Rollback order data only'
        )
        parser.add_argument(
            '--rollback-all',
            action='store_true',
            help='Rollback all migrated data'
        )
        parser.add_argument(
            '--restore-from-backup',
            type=str,
            help='Restore from specific backup file'
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm destructive operations'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.confirm = options['confirm']

        if self.dry_run:
            self.stdout.write(self.style.WARNING('Running in DRY-RUN mode - no data will be changed'))

        # Create backup directory if it doesn't exist
        self.backup_dir = os.path.join(settings.BASE_DIR, 'migration_backups')
        os.makedirs(self.backup_dir, exist_ok=True)

        # Initialize rollback statistics
        self.stats = {
            'users_deleted': 0,
            'addresses_deleted': 0,
            'products_deleted': 0,
            'product_images_deleted': 0,
            'product_tags_deleted': 0,
            'orders_deleted': 0,
            'order_items_deleted': 0,
            'membership_statuses_deleted': 0,
            'points_accounts_deleted': 0,
            'errors': []
        }

        try:
            # Handle different rollback operations
            if options['restore_from_backup']:
                self.restore_from_backup(options['restore_from_backup'])
            elif options['backup_first']:
                self.create_backup()
            elif options['rollback_all']:
                if not self.confirm:
                    raise CommandError('--rollback-all requires --confirm flag for safety')
                self.rollback_all()
            elif options['rollback_users']:
                self.rollback_users()
            elif options['rollback_products']:
                self.rollback_products()
            elif options['rollback_orders']:
                self.rollback_orders()
            else:
                self.stdout.write(self.style.ERROR('Please specify a rollback operation'))
                return

            # Print rollback statistics
            self.print_rollback_stats()

        except Exception as e:
            logger.error(f'Rollback failed: {e}')
            raise CommandError(f'Rollback failed: {e}')

    def create_backup(self):
        """Create backup of current Django data"""
        self.stdout.write('Creating backup of current data...')
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(self.backup_dir, f'django_backup_{timestamp}.json')
        
        # Models to backup
        models_to_backup = [
            User, Address, Product, ProductImage, ProductTag, Category,
            Order, OrderItem, ReturnOrder, OrderDiscount,
            MembershipStatus, TierUpgradeLog, PointsAccount, PointsTransaction
        ]
        
        backup_data = []
        
        for model in models_to_backup:
            try:
                queryset = model.objects.all()
                serialized = serializers.serialize('json', queryset)
                backup_data.append({
                    'model': f'{model._meta.app_label}.{model._meta.model_name}',
                    'count': queryset.count(),
                    'data': json.loads(serialized)
                })
                self.stdout.write(f'Backed up {queryset.count()} {model._meta.verbose_name_plural}')
            except Exception as e:
                error_msg = f'Error backing up {model._meta.model_name}: {e}'
                logger.error(error_msg)
                self.stats['errors'].append(error_msg)

        # Write backup to file
        try:
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.stdout.write(self.style.SUCCESS(f'Backup created: {backup_file}'))
            
            # Create metadata file
            metadata_file = backup_file.replace('.json', '_metadata.json')
            metadata = {
                'timestamp': timestamp,
                'backup_file': backup_file,
                'total_records': sum(item['count'] for item in backup_data),
                'models_backed_up': [item['model'] for item in backup_data]
            }
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            error_msg = f'Error writing backup file: {e}'
            logger.error(error_msg)
            raise CommandError(error_msg)

    def rollback_all(self):
        """Rollback all migrated data"""
        self.stdout.write(self.style.WARNING('Rolling back ALL migrated data...'))
        
        if not self.dry_run:
            # Confirm with user
            response = input('This will delete ALL migrated data. Type "DELETE ALL" to confirm: ')
            if response != 'DELETE ALL':
                self.stdout.write('Rollback cancelled.')
                return

        # Rollback in reverse dependency order
        self.rollback_orders()
        self.rollback_products()
        self.rollback_users()

    def rollback_users(self):
        """Rollback user-related data"""
        self.stdout.write('Rolling back user data...')
        
        try:
            with transaction.atomic():
                # Delete in dependency order
                
                # Points transactions
                if not self.dry_run:
                    deleted_count = PointsTransaction.objects.all().delete()[0]
                    self.stats['points_accounts_deleted'] += deleted_count
                else:
                    self.stats['points_accounts_deleted'] += PointsTransaction.objects.count()
                
                # Points accounts
                if not self.dry_run:
                    deleted_count = PointsAccount.objects.all().delete()[0]
                    self.stats['points_accounts_deleted'] += deleted_count
                else:
                    self.stats['points_accounts_deleted'] += PointsAccount.objects.count()
                
                # Tier upgrade logs
                if not self.dry_run:
                    deleted_count = TierUpgradeLog.objects.all().delete()[0]
                    self.stats['membership_statuses_deleted'] += deleted_count
                else:
                    self.stats['membership_statuses_deleted'] += TierUpgradeLog.objects.count()
                
                # Membership statuses
                if not self.dry_run:
                    deleted_count = MembershipStatus.objects.all().delete()[0]
                    self.stats['membership_statuses_deleted'] += deleted_count
                else:
                    self.stats['membership_statuses_deleted'] += MembershipStatus.objects.count()
                
                # Addresses
                if not self.dry_run:
                    deleted_count = Address.objects.all().delete()[0]
                    self.stats['addresses_deleted'] += deleted_count
                else:
                    self.stats['addresses_deleted'] += Address.objects.count()
                
                # Users (excluding superusers and staff created before migration)
                users_to_delete = User.objects.filter(
                    wechat_openid__isnull=False  # Only delete users with WeChat data (migrated users)
                ).exclude(
                    is_superuser=True  # Keep superusers
                )
                
                if not self.dry_run:
                    deleted_count = users_to_delete.delete()[0]
                    self.stats['users_deleted'] += deleted_count
                else:
                    self.stats['users_deleted'] += users_to_delete.count()

        except Exception as e:
            error_msg = f'Error rolling back users: {e}'
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)

    def rollback_products(self):
        """Rollback product-related data"""
        self.stdout.write('Rolling back product data...')
        
        try:
            with transaction.atomic():
                # Delete in dependency order
                
                # Product tags
                if not self.dry_run:
                    deleted_count = ProductTag.objects.all().delete()[0]
                    self.stats['product_tags_deleted'] += deleted_count
                else:
                    self.stats['product_tags_deleted'] += ProductTag.objects.count()
                
                # Product images
                if not self.dry_run:
                    deleted_count = ProductImage.objects.all().delete()[0]
                    self.stats['product_images_deleted'] += deleted_count
                else:
                    self.stats['product_images_deleted'] += ProductImage.objects.count()
                
                # Products (only those with gid - migrated products)
                products_to_delete = Product.objects.filter(gid__isnull=False)
                
                if not self.dry_run:
                    deleted_count = products_to_delete.delete()[0]
                    self.stats['products_deleted'] += deleted_count
                else:
                    self.stats['products_deleted'] += products_to_delete.count()

        except Exception as e:
            error_msg = f'Error rolling back products: {e}'
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)

    def rollback_orders(self):
        """Rollback order-related data"""
        self.stdout.write('Rolling back order data...')
        
        try:
            with transaction.atomic():
                # Delete in dependency order
                
                # Order discounts
                if not self.dry_run:
                    deleted_count = OrderDiscount.objects.all().delete()[0]
                    self.stats['orders_deleted'] += deleted_count
                else:
                    self.stats['orders_deleted'] += OrderDiscount.objects.count()
                
                # Return orders
                if not self.dry_run:
                    deleted_count = ReturnOrder.objects.all().delete()[0]
                    self.stats['orders_deleted'] += deleted_count
                else:
                    self.stats['orders_deleted'] += ReturnOrder.objects.count()
                
                # Order items
                if not self.dry_run:
                    deleted_count = OrderItem.objects.all().delete()[0]
                    self.stats['order_items_deleted'] += deleted_count
                else:
                    self.stats['order_items_deleted'] += OrderItem.objects.count()
                
                # Orders (only those with roid - migrated orders)
                orders_to_delete = Order.objects.filter(roid__isnull=False)
                
                if not self.dry_run:
                    deleted_count = orders_to_delete.delete()[0]
                    self.stats['orders_deleted'] += deleted_count
                else:
                    self.stats['orders_deleted'] += orders_to_delete.count()

        except Exception as e:
            error_msg = f'Error rolling back orders: {e}'
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)

    def restore_from_backup(self, backup_file):
        """Restore data from backup file"""
        self.stdout.write(f'Restoring from backup: {backup_file}')
        
        if not os.path.exists(backup_file):
            raise CommandError(f'Backup file not found: {backup_file}')
        
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # First, clear existing data (with confirmation)
            if not self.dry_run:
                response = input('This will replace ALL current data with backup. Type "RESTORE" to confirm: ')
                if response != 'RESTORE':
                    self.stdout.write('Restore cancelled.')
                    return
                
                # Clear existing data
                self.rollback_all()
            
            # Restore data from backup
            for model_data in backup_data:
                model_name = model_data['model']
                records = model_data['data']
                
                self.stdout.write(f'Restoring {len(records)} {model_name} records...')
                
                if not self.dry_run:
                    # Use Django's deserialization
                    for obj in serializers.deserialize('json', json.dumps(records)):
                        obj.save()
                
                self.stdout.write(f'Restored {len(records)} {model_name} records')
            
            self.stdout.write(self.style.SUCCESS('Restore completed successfully'))
            
        except Exception as e:
            error_msg = f'Error restoring from backup: {e}'
            logger.error(error_msg)
            raise CommandError(error_msg)

    def print_rollback_stats(self):
        """Print rollback statistics"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('ROLLBACK COMPLETED'))
        self.stdout.write('='*50)
        
        self.stdout.write(f"Users deleted: {self.stats['users_deleted']}")
        self.stdout.write(f"Addresses deleted: {self.stats['addresses_deleted']}")
        self.stdout.write(f"Products deleted: {self.stats['products_deleted']}")
        self.stdout.write(f"Product images deleted: {self.stats['product_images_deleted']}")
        self.stdout.write(f"Product tags deleted: {self.stats['product_tags_deleted']}")
        self.stdout.write(f"Orders deleted: {self.stats['orders_deleted']}")
        self.stdout.write(f"Order items deleted: {self.stats['order_items_deleted']}")
        self.stdout.write(f"Membership statuses deleted: {self.stats['membership_statuses_deleted']}")
        self.stdout.write(f"Points accounts deleted: {self.stats['points_accounts_deleted']}")
        
        if self.stats['errors']:
            self.stdout.write(f"\nErrors encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                self.stdout.write(self.style.ERROR(f"  - {error}"))
            if len(self.stats['errors']) > 5:
                self.stdout.write(f"  ... and {len(self.stats['errors']) - 5} more errors")
        else:
            self.stdout.write(self.style.SUCCESS("\nNo errors encountered!"))
        
        self.stdout.write('='*50)