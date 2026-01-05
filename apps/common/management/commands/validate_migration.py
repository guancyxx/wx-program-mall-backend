"""
Data migration validation script to verify integrity between MongoDB source and MySQL destination

This script validates:
1. User data integrity and completeness
2. Product data integrity and relationships
3. Order data integrity and relationships
4. Cross-reference validation between related models

Usage:
    python manage.py validate_migration --mongodb-uri "mongodb://localhost:27017/your_db"
    python manage.py validate_migration --mongodb-uri "mongodb://localhost:27017/your_db" --detailed
"""

import logging
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum

# Import Django models
from apps.users.models import Address
from apps.products.models import Product, ProductImage, ProductTag
from apps.orders.models import Order, OrderItem
from apps.membership.models import MembershipStatus
from apps.points.models import PointsAccount

User = get_user_model()

# Setup logging
logger = logging.getLogger(__name__)

try:
    import pymongo
    from pymongo import MongoClient
except ImportError:
    raise CommandError("pymongo is required for validation. Install with: pip install pymongo")


class Command(BaseCommand):
    help = 'Validate data migration integrity between MongoDB and MySQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mongodb-uri',
            type=str,
            required=True,
            help='MongoDB connection URI (e.g., mongodb://localhost:27017/database_name)'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed validation results'
        )
        parser.add_argument(
            '--sample-size',
            type=int,
            default=100,
            help='Number of records to sample for detailed validation (default: 100)'
        )

    def handle(self, *args, **options):
        self.detailed = options['detailed']
        self.sample_size = options['sample_size']
        mongodb_uri = options['mongodb_uri']

        try:
            # Connect to MongoDB
            self.mongo_client = MongoClient(mongodb_uri)
            self.mongo_db = self.mongo_client.get_default_database()
            
            # Test connection
            self.mongo_client.admin.command('ping')
            self.stdout.write(self.style.SUCCESS(f'Connected to MongoDB: {mongodb_uri}'))

        except Exception as e:
            raise CommandError(f'Failed to connect to MongoDB: {e}')

        # Initialize validation results
        self.validation_results = {
            'users': {'passed': 0, 'failed': 0, 'issues': []},
            'products': {'passed': 0, 'failed': 0, 'issues': []},
            'orders': {'passed': 0, 'failed': 0, 'issues': []},
            'relationships': {'passed': 0, 'failed': 0, 'issues': []},
        }

        try:
            # Run validations
            self.validate_users()
            self.validate_products()
            self.validate_orders()
            self.validate_relationships()

            # Print validation results
            self.print_validation_results()

        except Exception as e:
            logger.error(f'Validation failed: {e}')
            raise CommandError(f'Validation failed: {e}')
        
        finally:
            self.mongo_client.close()

    def validate_users(self):
        """Validate user data migration"""
        self.stdout.write('Validating user data...')
        
        # Count validation
        mongo_users = self.mongo_db['users'].count_documents({})
        django_users = User.objects.count()
        
        self.stdout.write(f'MongoDB users: {mongo_users}')
        self.stdout.write(f'Django users: {django_users}')
        
        if mongo_users != django_users:
            issue = f'User count mismatch: MongoDB={mongo_users}, Django={django_users}'
            self.validation_results['users']['issues'].append(issue)
            self.validation_results['users']['failed'] += 1
        else:
            self.validation_results['users']['passed'] += 1

        # Sample detailed validation
        if self.detailed:
            self.validate_user_samples()

        # Validate addresses
        self.validate_addresses()

        # Validate membership status creation
        users_with_membership = MembershipStatus.objects.count()
        if users_with_membership != django_users:
            issue = f'Membership status count mismatch: Expected={django_users}, Actual={users_with_membership}'
            self.validation_results['users']['issues'].append(issue)
            self.validation_results['users']['failed'] += 1

        # Validate points accounts creation
        users_with_points = PointsAccount.objects.count()
        if users_with_points != django_users:
            issue = f'Points account count mismatch: Expected={django_users}, Actual={users_with_points}'
            self.validation_results['users']['issues'].append(issue)
            self.validation_results['users']['failed'] += 1

    def validate_user_samples(self):
        """Validate a sample of user records in detail"""
        self.stdout.write(f'Validating {self.sample_size} user samples...')
        
        # Get sample of MongoDB users
        mongo_users = list(self.mongo_db['users'].find().limit(self.sample_size))
        
        for mongo_user in mongo_users:
            try:
                # Find corresponding Django user
                django_user = User.objects.get(wechat_openid=mongo_user.get('openId'))
                
                # Validate key fields
                issues = []
                
                # Check username
                expected_username = mongo_user.get('nickName') or f"user_{mongo_user.get('uid', 'unknown')}"
                if django_user.username != expected_username[:150]:
                    issues.append(f'Username mismatch for user {mongo_user.get("uid")}')
                
                # Check phone
                mongo_phone = mongo_user.get('phone', '').strip() or None
                if django_user.phone != mongo_phone:
                    issues.append(f'Phone mismatch for user {mongo_user.get("uid")}')
                
                # Check WeChat data
                if django_user.wechat_openid != mongo_user.get('openId'):
                    issues.append(f'OpenID mismatch for user {mongo_user.get("uid")}')
                
                if django_user.wechat_session_key != mongo_user.get('session_key'):
                    issues.append(f'Session key mismatch for user {mongo_user.get("uid")}')
                
                # Check admin status
                expected_is_staff = mongo_user.get('roles', 1) == 0
                if django_user.is_staff != expected_is_staff:
                    issues.append(f'Admin status mismatch for user {mongo_user.get("uid")}')
                
                if issues:
                    self.validation_results['users']['issues'].extend(issues)
                    self.validation_results['users']['failed'] += len(issues)
                else:
                    self.validation_results['users']['passed'] += 1
                    
            except User.DoesNotExist:
                issue = f'User {mongo_user.get("uid")} not found in Django'
                self.validation_results['users']['issues'].append(issue)
                self.validation_results['users']['failed'] += 1
            except Exception as e:
                issue = f'Error validating user {mongo_user.get("uid")}: {e}'
                self.validation_results['users']['issues'].append(issue)
                self.validation_results['users']['failed'] += 1

    def validate_addresses(self):
        """Validate address migration"""
        self.stdout.write('Validating addresses...')
        
        # Count total addresses in MongoDB
        mongo_address_count = 0
        for user_doc in self.mongo_db['users'].find({'address': {'$exists': True, '$ne': []}}):
            mongo_address_count += len(user_doc.get('address', []))
        
        django_address_count = Address.objects.count()
        
        self.stdout.write(f'MongoDB addresses: {mongo_address_count}')
        self.stdout.write(f'Django addresses: {django_address_count}')
        
        if mongo_address_count != django_address_count:
            issue = f'Address count mismatch: MongoDB={mongo_address_count}, Django={django_address_count}'
            self.validation_results['users']['issues'].append(issue)
            self.validation_results['users']['failed'] += 1
        else:
            self.validation_results['users']['passed'] += 1

    def validate_products(self):
        """Validate product data migration"""
        self.stdout.write('Validating product data...')
        
        # Count validation
        mongo_products = self.mongo_db['goods'].count_documents({})
        django_products = Product.objects.count()
        
        self.stdout.write(f'MongoDB products: {mongo_products}')
        self.stdout.write(f'Django products: {django_products}')
        
        if mongo_products != django_products:
            issue = f'Product count mismatch: MongoDB={mongo_products}, Django={django_products}'
            self.validation_results['products']['issues'].append(issue)
            self.validation_results['products']['failed'] += 1
        else:
            self.validation_results['products']['passed'] += 1

        # Validate product images
        self.validate_product_images()
        
        # Validate product tags
        self.validate_product_tags()

        # Sample detailed validation
        if self.detailed:
            self.validate_product_samples()

    def validate_product_images(self):
        """Validate product image migration"""
        self.stdout.write('Validating product images...')
        
        # Count total images in MongoDB
        mongo_image_count = 0
        for product_doc in self.mongo_db['goods'].find({'images': {'$exists': True, '$ne': []}}):
            mongo_image_count += len(product_doc.get('images', []))
        
        django_image_count = ProductImage.objects.count()
        
        self.stdout.write(f'MongoDB product images: {mongo_image_count}')
        self.stdout.write(f'Django product images: {django_image_count}')
        
        if mongo_image_count != django_image_count:
            issue = f'Product image count mismatch: MongoDB={mongo_image_count}, Django={django_image_count}'
            self.validation_results['products']['issues'].append(issue)
            self.validation_results['products']['failed'] += 1
        else:
            self.validation_results['products']['passed'] += 1

    def validate_product_tags(self):
        """Validate product tag migration"""
        self.stdout.write('Validating product tags...')
        
        # Count total tags in MongoDB
        mongo_tag_count = 0
        for product_doc in self.mongo_db['goods'].find({'tags': {'$exists': True, '$ne': []}}):
            mongo_tag_count += len(product_doc.get('tags', []))
        
        django_tag_count = ProductTag.objects.count()
        
        self.stdout.write(f'MongoDB product tags: {mongo_tag_count}')
        self.stdout.write(f'Django product tags: {django_tag_count}')
        
        if mongo_tag_count != django_tag_count:
            issue = f'Product tag count mismatch: MongoDB={mongo_tag_count}, Django={django_tag_count}'
            self.validation_results['products']['issues'].append(issue)
            self.validation_results['products']['failed'] += 1
        else:
            self.validation_results['products']['passed'] += 1

    def validate_product_samples(self):
        """Validate a sample of product records in detail"""
        self.stdout.write(f'Validating {self.sample_size} product samples...')
        
        # Get sample of MongoDB products
        mongo_products = list(self.mongo_db['goods'].find().limit(self.sample_size))
        
        for mongo_product in mongo_products:
            try:
                # Find corresponding Django product
                django_product = Product.objects.get(gid=mongo_product.get('gid'))
                
                # Validate key fields
                issues = []
                
                # Check basic fields
                if django_product.name != mongo_product.get('name', ''):
                    issues.append(f'Name mismatch for product {mongo_product.get("gid")}')
                
                if django_product.price != Decimal(str(mongo_product.get('price', 0))):
                    issues.append(f'Price mismatch for product {mongo_product.get("gid")}')
                
                if django_product.status != mongo_product.get('status', 1):
                    issues.append(f'Status mismatch for product {mongo_product.get("gid")}')
                
                if django_product.inventory != mongo_product.get('inventory', 0):
                    issues.append(f'Inventory mismatch for product {mongo_product.get("gid")}')
                
                if issues:
                    self.validation_results['products']['issues'].extend(issues)
                    self.validation_results['products']['failed'] += len(issues)
                else:
                    self.validation_results['products']['passed'] += 1
                    
            except Product.DoesNotExist:
                issue = f'Product {mongo_product.get("gid")} not found in Django'
                self.validation_results['products']['issues'].append(issue)
                self.validation_results['products']['failed'] += 1
            except Exception as e:
                issue = f'Error validating product {mongo_product.get("gid")}: {e}'
                self.validation_results['products']['issues'].append(issue)
                self.validation_results['products']['failed'] += 1

    def validate_orders(self):
        """Validate order data migration"""
        self.stdout.write('Validating order data...')
        
        # Count validation
        mongo_orders = self.mongo_db['order'].count_documents({})
        django_orders = Order.objects.count()
        
        self.stdout.write(f'MongoDB orders: {mongo_orders}')
        self.stdout.write(f'Django orders: {django_orders}')
        
        # Note: Django orders might be less than MongoDB orders if some users weren't migrated
        if django_orders > mongo_orders:
            issue = f'Order count unexpected: MongoDB={mongo_orders}, Django={django_orders}'
            self.validation_results['orders']['issues'].append(issue)
            self.validation_results['orders']['failed'] += 1
        else:
            self.validation_results['orders']['passed'] += 1

        # Validate order items
        self.validate_order_items()

        # Sample detailed validation
        if self.detailed:
            self.validate_order_samples()

    def validate_order_items(self):
        """Validate order item migration"""
        self.stdout.write('Validating order items...')
        
        # Count total order items in MongoDB
        mongo_item_count = 0
        for order_doc in self.mongo_db['order'].find({'goods': {'$exists': True, '$ne': []}}):
            mongo_item_count += len(order_doc.get('goods', []))
        
        django_item_count = OrderItem.objects.count()
        
        self.stdout.write(f'MongoDB order items: {mongo_item_count}')
        self.stdout.write(f'Django order items: {django_item_count}')
        
        # Django items might be less if some orders weren't migrated
        if django_item_count > mongo_item_count:
            issue = f'Order item count unexpected: MongoDB={mongo_item_count}, Django={django_item_count}'
            self.validation_results['orders']['issues'].append(issue)
            self.validation_results['orders']['failed'] += 1
        else:
            self.validation_results['orders']['passed'] += 1

    def validate_order_samples(self):
        """Validate a sample of order records in detail"""
        self.stdout.write(f'Validating {self.sample_size} order samples...')
        
        # Get sample of MongoDB orders
        mongo_orders = list(self.mongo_db['order'].find().limit(self.sample_size))
        
        for mongo_order in mongo_orders:
            try:
                # Find corresponding Django order
                django_order = Order.objects.get(roid=mongo_order.get('roid'))
                
                # Validate key fields
                issues = []
                
                # Check basic fields
                if django_order.amount != Decimal(str(mongo_order.get('amount', 0))):
                    issues.append(f'Amount mismatch for order {mongo_order.get("roid")}')
                
                if django_order.status != mongo_order.get('status', -1):
                    issues.append(f'Status mismatch for order {mongo_order.get("roid")}')
                
                if django_order.type != mongo_order.get('type', 2):
                    issues.append(f'Type mismatch for order {mongo_order.get("roid")}')
                
                # Check order items count
                mongo_items_count = len(mongo_order.get('goods', []))
                django_items_count = django_order.items.count()
                
                if mongo_items_count != django_items_count:
                    issues.append(f'Order items count mismatch for order {mongo_order.get("roid")}: MongoDB={mongo_items_count}, Django={django_items_count}')
                
                if issues:
                    self.validation_results['orders']['issues'].extend(issues)
                    self.validation_results['orders']['failed'] += len(issues)
                else:
                    self.validation_results['orders']['passed'] += 1
                    
            except Order.DoesNotExist:
                issue = f'Order {mongo_order.get("roid")} not found in Django'
                self.validation_results['orders']['issues'].append(issue)
                self.validation_results['orders']['failed'] += 1
            except Exception as e:
                issue = f'Error validating order {mongo_order.get("roid")}: {e}'
                self.validation_results['orders']['issues'].append(issue)
                self.validation_results['orders']['failed'] += 1

    def validate_relationships(self):
        """Validate relationships and referential integrity"""
        self.stdout.write('Validating relationships...')
        
        # Check for orphaned records
        orphaned_addresses = Address.objects.filter(user__isnull=True).count()
        if orphaned_addresses > 0:
            issue = f'Found {orphaned_addresses} orphaned addresses'
            self.validation_results['relationships']['issues'].append(issue)
            self.validation_results['relationships']['failed'] += 1
        
        orphaned_images = ProductImage.objects.filter(product__isnull=True).count()
        if orphaned_images > 0:
            issue = f'Found {orphaned_images} orphaned product images'
            self.validation_results['relationships']['issues'].append(issue)
            self.validation_results['relationships']['failed'] += 1
        
        orphaned_tags = ProductTag.objects.filter(product__isnull=True).count()
        if orphaned_tags > 0:
            issue = f'Found {orphaned_tags} orphaned product tags'
            self.validation_results['relationships']['issues'].append(issue)
            self.validation_results['relationships']['failed'] += 1
        
        orphaned_order_items = OrderItem.objects.filter(order__isnull=True).count()
        if orphaned_order_items > 0:
            issue = f'Found {orphaned_order_items} orphaned order items'
            self.validation_results['relationships']['issues'].append(issue)
            self.validation_results['relationships']['failed'] += 1
        
        # Check for missing required relationships
        users_without_membership = User.objects.filter(membership_status__isnull=True).count()
        if users_without_membership > 0:
            issue = f'Found {users_without_membership} users without membership status'
            self.validation_results['relationships']['issues'].append(issue)
            self.validation_results['relationships']['failed'] += 1
        
        users_without_points = User.objects.filter(points_account__isnull=True).count()
        if users_without_points > 0:
            issue = f'Found {users_without_points} users without points account'
            self.validation_results['relationships']['issues'].append(issue)
            self.validation_results['relationships']['failed'] += 1
        
        if not self.validation_results['relationships']['issues']:
            self.validation_results['relationships']['passed'] += 1

    def print_validation_results(self):
        """Print validation results"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('VALIDATION RESULTS'))
        self.stdout.write('='*60)
        
        total_passed = 0
        total_failed = 0
        
        for category, results in self.validation_results.items():
            passed = results['passed']
            failed = results['failed']
            total_passed += passed
            total_failed += failed
            
            status_style = self.style.SUCCESS if failed == 0 else self.style.ERROR
            self.stdout.write(f"\n{category.upper()}:")
            self.stdout.write(status_style(f"  Passed: {passed}, Failed: {failed}"))
            
            if results['issues'] and self.detailed:
                self.stdout.write("  Issues:")
                for issue in results['issues'][:5]:  # Show first 5 issues
                    self.stdout.write(f"    - {issue}")
                if len(results['issues']) > 5:
                    self.stdout.write(f"    ... and {len(results['issues']) - 5} more issues")
        
        self.stdout.write(f"\nOVERALL SUMMARY:")
        overall_style = self.style.SUCCESS if total_failed == 0 else self.style.ERROR
        self.stdout.write(overall_style(f"Total Passed: {total_passed}, Total Failed: {total_failed}"))
        
        if total_failed == 0:
            self.stdout.write(self.style.SUCCESS("\n✓ All validations passed! Migration integrity verified."))
        else:
            self.stdout.write(self.style.ERROR(f"\n✗ {total_failed} validation issues found. Please review and fix."))
        
        self.stdout.write('='*60)