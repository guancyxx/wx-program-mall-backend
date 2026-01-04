"""
Data migration script to transfer data from Node.js/MongoDB to Django/MySQL

This script migrates:
1. User data (users collection -> User and Address models)
2. Product data (goods collection -> Product, ProductImage, ProductTag models)
3. Order data (order collection -> Order, OrderItem, ReturnOrder models)

Usage:
    python manage.py migrate_from_mongodb --mongodb-uri "mongodb://localhost:27017/your_db" --dry-run
    python manage.py migrate_from_mongodb --mongodb-uri "mongodb://localhost:27017/your_db"
"""

import logging
from decimal import Decimal
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
import json

# Import Django models
from apps.users.models import Address
from apps.products.models import Product, ProductImage, ProductTag, Category
from apps.orders.models import Order, OrderItem, ReturnOrder
from apps.membership.models import MembershipTier, MembershipStatus
from apps.points.models import PointsAccount

User = get_user_model()

# Setup logging
logger = logging.getLogger(__name__)

try:
    import pymongo
    from pymongo import MongoClient
except ImportError:
    raise CommandError("pymongo is required for this migration. Install with: pip install pymongo")


class Command(BaseCommand):
    help = 'Migrate data from Node.js/MongoDB to Django/MySQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mongodb-uri',
            type=str,
            required=True,
            help='MongoDB connection URI (e.g., mongodb://localhost:27017/database_name)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run migration in dry-run mode (no actual data changes)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of records to process in each batch (default: 100)'
        )
        parser.add_argument(
            '--skip-users',
            action='store_true',
            help='Skip user data migration'
        )
        parser.add_argument(
            '--skip-products',
            action='store_true',
            help='Skip product data migration'
        )
        parser.add_argument(
            '--skip-orders',
            action='store_true',
            help='Skip order data migration'
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.batch_size = options['batch_size']
        mongodb_uri = options['mongodb_uri']

        if self.dry_run:
            self.stdout.write(self.style.WARNING('Running in DRY-RUN mode - no data will be changed'))

        try:
            # Connect to MongoDB
            self.mongo_client = MongoClient(mongodb_uri)
            self.mongo_db = self.mongo_client.get_default_database()
            
            # Test connection
            self.mongo_client.admin.command('ping')
            self.stdout.write(self.style.SUCCESS(f'Connected to MongoDB: {mongodb_uri}'))

        except Exception as e:
            raise CommandError(f'Failed to connect to MongoDB: {e}')

        # Initialize migration statistics
        self.stats = {
            'users_migrated': 0,
            'addresses_migrated': 0,
            'products_migrated': 0,
            'product_images_migrated': 0,
            'product_tags_migrated': 0,
            'orders_migrated': 0,
            'order_items_migrated': 0,
            'return_orders_migrated': 0,
            'errors': []
        }

        try:
            # Run migrations in order
            if not options['skip_users']:
                self.migrate_users()
            
            if not options['skip_products']:
                self.migrate_products()
            
            if not options['skip_orders']:
                self.migrate_orders()

            # Print final statistics
            self.print_migration_stats()

        except Exception as e:
            logger.error(f'Migration failed: {e}')
            raise CommandError(f'Migration failed: {e}')
        
        finally:
            self.mongo_client.close()

    def migrate_users(self):
        """Migrate user data from MongoDB users collection"""
        self.stdout.write('Migrating users...')
        
        users_collection = self.mongo_db['users']
        total_users = users_collection.count_documents({})
        
        self.stdout.write(f'Found {total_users} users to migrate')

        # Get default Bronze tier for new users
        try:
            bronze_tier = MembershipTier.objects.get(name='Bronze')
        except MembershipTier.DoesNotExist:
            self.stdout.write(self.style.WARNING('Bronze tier not found. Creating default tiers...'))
            if not self.dry_run:
                self.create_default_tiers()
                bronze_tier = MembershipTier.objects.get(name='Bronze')
            else:
                bronze_tier = None

        processed = 0
        for user_doc in users_collection.find().batch_size(self.batch_size):
            try:
                with transaction.atomic():
                    if not self.dry_run:
                        # Create or update user
                        user_data = self.convert_user_data(user_doc)
                        user, created = User.objects.update_or_create(
                            wechat_openid=user_data.get('wechat_openid'),
                            defaults=user_data
                        )
                        
                        # Create membership status if user was created
                        if created and bronze_tier:
                            MembershipStatus.objects.create(
                                user=user,
                                tier=bronze_tier,
                                total_spending=Decimal('0.00')
                            )
                            
                            # Create points account
                            PointsAccount.objects.create(
                                user=user,
                                balance=0,
                                total_earned=0,
                                total_spent=0
                            )

                        # Migrate addresses
                        if 'address' in user_doc and user_doc['address']:
                            self.migrate_user_addresses(user, user_doc['address'])

                        self.stats['users_migrated'] += 1
                    else:
                        # Dry run - just validate data
                        self.convert_user_data(user_doc)
                        self.stats['users_migrated'] += 1

                processed += 1
                if processed % 50 == 0:
                    self.stdout.write(f'Processed {processed}/{total_users} users')

            except Exception as e:
                error_msg = f'Error migrating user {user_doc.get("uid", "unknown")}: {e}'
                logger.error(error_msg)
                self.stats['errors'].append(error_msg)

        self.stdout.write(self.style.SUCCESS(f'Users migration completed: {self.stats["users_migrated"]} users'))

    def convert_user_data(self, user_doc):
        """Convert MongoDB user document to Django User model data"""
        # Handle username - use nickName or generate from uid
        username = user_doc.get('nickName') or f"user_{user_doc.get('uid', 'unknown')}"
        
        # Ensure username is unique and valid
        if len(username) > 150:
            username = username[:150]
        
        # Handle phone number
        phone = user_doc.get('phone', '').strip()
        if not phone:
            phone = None

        # Convert timestamps
        created_at = self.parse_chinese_datetime(user_doc.get('createTime'))
        last_login = self.parse_chinese_datetime(user_doc.get('lastLoginTime'))

        return {
            'username': username,
            'phone': phone,
            'wechat_openid': user_doc.get('openId'),
            'wechat_session_key': user_doc.get('session_key'),
            'avatar': user_doc.get('avatar', ''),
            'is_staff': user_doc.get('roles', 1) == 0,  # 0 is admin in Node.js
            'is_active': True,
            'date_joined': created_at or timezone.now(),
            'last_login': last_login,
        }

    def migrate_user_addresses(self, user, addresses_array):
        """Migrate user addresses from MongoDB array to Django Address model"""
        for i, addr_data in enumerate(addresses_array):
            try:
                if not self.dry_run:
                    Address.objects.create(
                        user=user,
                        name=addr_data.get('name', ''),
                        phone=addr_data.get('phone', ''),
                        address=addr_data.get('address', ''),
                        detail=addr_data.get('detail', ''),
                        address_type=addr_data.get('type', 0),
                        is_default=(i == 0)  # First address as default
                    )
                self.stats['addresses_migrated'] += 1
            except Exception as e:
                error_msg = f'Error migrating address for user {user.id}: {e}'
                logger.error(error_msg)
                self.stats['errors'].append(error_msg)

    def migrate_products(self):
        """Migrate product data from MongoDB goods collection"""
        self.stdout.write('Migrating products...')
        
        goods_collection = self.mongo_db['goods']
        total_products = goods_collection.count_documents({})
        
        self.stdout.write(f'Found {total_products} products to migrate')

        processed = 0
        for product_doc in goods_collection.find().batch_size(self.batch_size):
            try:
                with transaction.atomic():
                    if not self.dry_run:
                        # Create or update product
                        product_data = self.convert_product_data(product_doc)
                        product, created = Product.objects.update_or_create(
                            gid=product_data['gid'],
                            defaults=product_data
                        )

                        # Migrate product images
                        if 'images' in product_doc and product_doc['images']:
                            self.migrate_product_images(product, product_doc['images'])

                        # Migrate product tags
                        if 'tags' in product_doc and product_doc['tags']:
                            self.migrate_product_tags(product, product_doc['tags'])

                        self.stats['products_migrated'] += 1
                    else:
                        # Dry run - just validate data
                        self.convert_product_data(product_doc)
                        self.stats['products_migrated'] += 1

                processed += 1
                if processed % 50 == 0:
                    self.stdout.write(f'Processed {processed}/{total_products} products')

            except Exception as e:
                error_msg = f'Error migrating product {product_doc.get("gid", "unknown")}: {e}'
                logger.error(error_msg)
                self.stats['errors'].append(error_msg)

        self.stdout.write(self.style.SUCCESS(f'Products migration completed: {self.stats["products_migrated"]} products'))

    def convert_product_data(self, product_doc):
        """Convert MongoDB goods document to Django Product model data"""
        return {
            'gid': product_doc.get('gid', ''),
            'name': product_doc.get('name', ''),
            'price': Decimal(str(product_doc.get('price', 0))),
            'dis_price': Decimal(str(product_doc.get('disPrice', 0))) if product_doc.get('disPrice') else None,
            'description': product_doc.get('description', ''),
            'content': product_doc.get('content', ''),
            'status': product_doc.get('status', 1),
            'has_top': product_doc.get('hasTop', 0),
            'has_recommend': product_doc.get('hasRecommend', 0),
            'inventory': product_doc.get('inventory', 0),
            'sold': product_doc.get('sold', 0),
            'views': product_doc.get('views', 0),
            'create_time': product_doc.get('createTime') or timezone.now(),
            'update_time': product_doc.get('updateTime') or timezone.now(),
        }

    def migrate_product_images(self, product, images_array):
        """Migrate product images from MongoDB array to Django ProductImage model"""
        # Clear existing images for this product
        if not self.dry_run:
            ProductImage.objects.filter(product=product).delete()

        for i, image_url in enumerate(images_array):
            try:
                if not self.dry_run:
                    ProductImage.objects.create(
                        product=product,
                        image_url=image_url,
                        is_primary=(i == 0),  # First image as primary
                        order=i
                    )
                self.stats['product_images_migrated'] += 1
            except Exception as e:
                error_msg = f'Error migrating image for product {product.gid}: {e}'
                logger.error(error_msg)
                self.stats['errors'].append(error_msg)

    def migrate_product_tags(self, product, tags_array):
        """Migrate product tags from MongoDB array to Django ProductTag model"""
        # Clear existing tags for this product
        if not self.dry_run:
            ProductTag.objects.filter(product=product).delete()

        for tag in tags_array:
            try:
                if not self.dry_run:
                    ProductTag.objects.create(
                        product=product,
                        tag=tag
                    )
                self.stats['product_tags_migrated'] += 1
            except Exception as e:
                error_msg = f'Error migrating tag for product {product.gid}: {e}'
                logger.error(error_msg)
                self.stats['errors'].append(error_msg)

    def migrate_orders(self):
        """Migrate order data from MongoDB order collection"""
        self.stdout.write('Migrating orders...')
        
        orders_collection = self.mongo_db['order']
        total_orders = orders_collection.count_documents({})
        
        self.stdout.write(f'Found {total_orders} orders to migrate')

        processed = 0
        for order_doc in orders_collection.find().batch_size(self.batch_size):
            try:
                with transaction.atomic():
                    if not self.dry_run:
                        # Find corresponding Django user
                        try:
                            user = User.objects.get(id=order_doc.get('uid'))
                        except User.DoesNotExist:
                            # Skip orders for non-existent users
                            continue

                        # Create or update order
                        order_data = self.convert_order_data(order_doc, user)
                        order, created = Order.objects.update_or_create(
                            roid=order_data['roid'],
                            defaults=order_data
                        )

                        # Migrate order items (goods array)
                        if 'goods' in order_doc and order_doc['goods']:
                            self.migrate_order_items(order, order_doc['goods'])

                        self.stats['orders_migrated'] += 1
                    else:
                        # Dry run - just validate data
                        self.convert_order_data(order_doc, None)
                        self.stats['orders_migrated'] += 1

                processed += 1
                if processed % 50 == 0:
                    self.stdout.write(f'Processed {processed}/{total_orders} orders')

            except Exception as e:
                error_msg = f'Error migrating order {order_doc.get("roid", "unknown")}: {e}'
                logger.error(error_msg)
                self.stats['errors'].append(error_msg)

        self.stdout.write(self.style.SUCCESS(f'Orders migration completed: {self.stats["orders_migrated"]} orders'))

    def convert_order_data(self, order_doc, user):
        """Convert MongoDB order document to Django Order model data"""
        # Handle refund info
        refund_info = order_doc.get('refundInfo', {})
        if isinstance(refund_info, dict):
            refund_info = refund_info
        else:
            refund_info = {}

        # Handle logistics info
        logistics = order_doc.get('logistics', {})
        if isinstance(logistics, dict):
            logistics = logistics
        else:
            logistics = {}

        # Handle address info
        address = order_doc.get('address', {})
        if isinstance(address, dict):
            address = address
        else:
            address = {}

        return {
            'roid': order_doc.get('roid', ''),
            'uid': user,
            'lid': order_doc.get('lid'),
            'create_time': order_doc.get('createTime') or timezone.now(),
            'pay_time': order_doc.get('payTime'),
            'send_time': order_doc.get('sendTime'),
            'amount': Decimal(str(order_doc.get('amount', 0))),
            'status': order_doc.get('status', -1),
            'refund_info': refund_info,
            'openid': order_doc.get('openid', ''),
            'type': order_doc.get('type', 2),
            'logistics': logistics,
            'remark': order_doc.get('remark', ''),
            'address': address,
            'lock_timeout': order_doc.get('lockTimeout'),
            'cancel_text': order_doc.get('cancelText', ''),
            'qrcode': order_doc.get('qrcode', ''),
            'verify_time': order_doc.get('verifyTime'),
            'verify_status': order_doc.get('verifyStatus', 0),
        }

    def migrate_order_items(self, order, goods_array):
        """Migrate order items from MongoDB goods array to Django OrderItem model"""
        # Clear existing items for this order
        if not self.dry_run:
            OrderItem.objects.filter(order=order).delete()

        for i, item_data in enumerate(goods_array):
            try:
                if not self.dry_run:
                    OrderItem.objects.create(
                        order=order,
                        rrid=f"{order.roid}_item_{i}",  # Generate unique item ID
                        gid=item_data.get('gid', ''),
                        quantity=item_data.get('quantity', 1),
                        price=Decimal(str(item_data.get('price', 0))),
                        amount=Decimal(str(item_data.get('amount', 0))),
                        product_info=item_data  # Store full item data as JSON
                    )
                self.stats['order_items_migrated'] += 1
            except Exception as e:
                error_msg = f'Error migrating order item for order {order.roid}: {e}'
                logger.error(error_msg)
                self.stats['errors'].append(error_msg)

    def parse_chinese_datetime(self, datetime_str):
        """Parse Chinese datetime string to Django datetime"""
        if not datetime_str:
            return None
        
        try:
            # Handle Chinese datetime format: "2024/1/3 下午8:30:00"
            # This is a simplified parser - may need adjustment based on actual format
            if isinstance(datetime_str, str):
                # Try to parse common formats
                formats = [
                    '%Y/%m/%d %H:%M:%S',
                    '%Y-%m-%d %H:%M:%S',
                    '%Y/%m/%d',
                    '%Y-%m-%d',
                ]
                
                for fmt in formats:
                    try:
                        dt = datetime.strptime(datetime_str.split()[0], fmt.split()[0])
                        return timezone.make_aware(dt)
                    except (ValueError, IndexError):
                        continue
                        
            elif isinstance(datetime_str, datetime):
                return timezone.make_aware(datetime_str)
                
        except Exception as e:
            logger.warning(f'Failed to parse datetime {datetime_str}: {e}')
        
        return None

    def create_default_tiers(self):
        """Create default membership tiers if they don't exist"""
        tiers = [
            {'name': 'Bronze', 'min_spending': 0, 'max_spending': 999.99, 'points_multiplier': 1.0},
            {'name': 'Silver', 'min_spending': 1000, 'max_spending': 4999.99, 'points_multiplier': 1.2},
            {'name': 'Gold', 'min_spending': 5000, 'max_spending': 19999.99, 'points_multiplier': 1.5},
            {'name': 'Platinum', 'min_spending': 20000, 'max_spending': None, 'points_multiplier': 2.0},
        ]
        
        for tier_data in tiers:
            MembershipTier.objects.get_or_create(
                name=tier_data['name'],
                defaults={
                    'min_spending': Decimal(str(tier_data['min_spending'])),
                    'max_spending': Decimal(str(tier_data['max_spending'])) if tier_data['max_spending'] else None,
                    'points_multiplier': Decimal(str(tier_data['points_multiplier'])),
                    'benefits': {}
                }
            )

    def print_migration_stats(self):
        """Print migration statistics"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('MIGRATION COMPLETED'))
        self.stdout.write('='*50)
        
        self.stdout.write(f"Users migrated: {self.stats['users_migrated']}")
        self.stdout.write(f"Addresses migrated: {self.stats['addresses_migrated']}")
        self.stdout.write(f"Products migrated: {self.stats['products_migrated']}")
        self.stdout.write(f"Product images migrated: {self.stats['product_images_migrated']}")
        self.stdout.write(f"Product tags migrated: {self.stats['product_tags_migrated']}")
        self.stdout.write(f"Orders migrated: {self.stats['orders_migrated']}")
        self.stdout.write(f"Order items migrated: {self.stats['order_items_migrated']}")
        
        if self.stats['errors']:
            self.stdout.write(f"\nErrors encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:10]:  # Show first 10 errors
                self.stdout.write(self.style.ERROR(f"  - {error}"))
            if len(self.stats['errors']) > 10:
                self.stdout.write(f"  ... and {len(self.stats['errors']) - 10} more errors")
        else:
            self.stdout.write(self.style.SUCCESS("\nNo errors encountered!"))
        
        self.stdout.write('='*50)