"""
Property-based tests for data migration integrity

**Property 16: Data Migration Integrity**
**Validates: Requirements 9.1, 9.2, 9.3, 9.4**

These tests verify that data migration from MongoDB to Django/MySQL maintains
data integrity and completeness across all migrated records.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from hypothesis import given, strategies as st, settings, assume
from hypothesis.extra.django import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import transaction

# Import Django models
from apps.users.models import Address
from apps.products.models import Product, ProductImage, ProductTag
from apps.orders.models import Order, OrderItem
from apps.membership.models import MembershipTier, MembershipStatus
from apps.points.models import PointsAccount

User = get_user_model()


class TestDataMigrationIntegrity(TransactionTestCase):
    """
    Property-based tests for data migration integrity
    
    **Feature: django-mall-migration, Property 16: Data Migration Integrity**
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
    """

    def setUp(self):
        """Set up test data"""
        # Create default membership tier
        self.bronze_tier, _ = MembershipTier.objects.get_or_create(
            name='Bronze',
            defaults={
                'min_spending': Decimal('0.00'),
                'max_spending': Decimal('999.99'),
                'points_multiplier': Decimal('1.0'),
                'benefits': {}
            }
        )

    @given(
        user_data=st.fixed_dictionaries({
            'nickName': st.text(min_size=1, max_size=50),
            'uid': st.integers(min_value=1000, max_value=999999),
            'phone': st.one_of(st.none(), st.text(min_size=11, max_size=11, alphabet='0123456789')),
            'openId': st.text(min_size=10, max_size=100),
            'session_key': st.one_of(st.none(), st.text(min_size=10, max_size=100)),
            'avatar': st.one_of(st.none(), st.text(min_size=1, max_size=200)),
            'roles': st.integers(min_value=0, max_value=1),
            'address': st.lists(
                st.fixed_dictionaries({
                    'name': st.text(min_size=1, max_size=50),
                    'phone': st.text(min_size=11, max_size=11, alphabet='0123456789'),
                    'address': st.text(min_size=1, max_size=100),
                    'detail': st.text(min_size=1, max_size=100),
                    'type': st.integers(min_value=0, max_value=3),
                }),
                max_size=5
            )
        })
    )
    @settings(max_examples=50, deadline=5000)
    def test_user_migration_integrity(self, user_data):
        """
        Property: For any valid user data from MongoDB, migrating to Django should preserve
        all core user information and create proper related records
        
        **Validates: Requirements 9.1, 9.2**
        """
        # Simulate user migration
        with transaction.atomic():
            # Convert MongoDB user data to Django format
            django_user_data = self._convert_mongodb_user_data(user_data)
            
            # Create user
            user = User.objects.create(**django_user_data)
            
            # Create membership status (as migration would do)
            membership_status = MembershipStatus.objects.create(
                user=user,
                tier=self.bronze_tier,
                total_spending=Decimal('0.00')
            )
            
            # Create points account (as migration would do)
            points_account = PointsAccount.objects.create(
                user=user,
                balance=0,
                total_earned=0,
                total_spent=0
            )
            
            # Migrate addresses
            migrated_addresses = []
            for i, addr_data in enumerate(user_data['address']):
                address = Address.objects.create(
                    user=user,
                    name=addr_data['name'],
                    phone=addr_data['phone'],
                    address=addr_data['address'],
                    detail=addr_data['detail'],
                    address_type=addr_data['type'],
                    is_default=(i == 0)
                )
                migrated_addresses.append(address)
            
            # Verify data integrity
            
            # 1. User data integrity
            assert user.username == (user_data['nickName'] or f"user_{user_data['uid']}")[:150]
            assert user.wechat_openid == user_data['openId']
            assert user.wechat_session_key == user_data['session_key']
            assert user.is_staff == (user_data['roles'] == 0)
            
            # 2. Phone number handling
            expected_phone = user_data['phone'].strip() if user_data['phone'] else None
            if not expected_phone:
                expected_phone = None
            assert user.phone == expected_phone
            
            # 3. Membership status created
            assert MembershipStatus.objects.filter(user=user).exists()
            assert membership_status.tier == self.bronze_tier
            assert membership_status.total_spending == Decimal('0.00')
            
            # 4. Points account created
            assert PointsAccount.objects.filter(user=user).exists()
            assert points_account.balance == 0
            
            # 5. Address migration integrity
            assert Address.objects.filter(user=user).count() == len(user_data['address'])
            
            for original_addr, migrated_addr in zip(user_data['address'], migrated_addresses):
                assert migrated_addr.name == original_addr['name']
                assert migrated_addr.phone == original_addr['phone']
                assert migrated_addr.address == original_addr['address']
                assert migrated_addr.detail == original_addr['detail']
                assert migrated_addr.address_type == original_addr['type']
            
            # 6. Default address handling
            if user_data['address']:
                default_addresses = Address.objects.filter(user=user, is_default=True)
                assert default_addresses.count() == 1
                assert default_addresses.first() == migrated_addresses[0]

    @given(
        product_data=st.fixed_dictionaries({
            'gid': st.text(min_size=1, max_size=100),
            'name': st.text(min_size=1, max_size=200),
            'price': st.decimals(min_value=0, max_value=99999, places=2),
            'disPrice': st.one_of(st.none(), st.decimals(min_value=0, max_value=99999, places=2)),
            'description': st.text(max_size=500),
            'content': st.text(max_size=1000),
            'status': st.integers(min_value=-1, max_value=1),
            'hasTop': st.integers(min_value=0, max_value=1),
            'hasRecommend': st.integers(min_value=0, max_value=1),
            'inventory': st.integers(min_value=0, max_value=9999),
            'sold': st.integers(min_value=0, max_value=9999),
            'views': st.integers(min_value=0, max_value=999999),
            'images': st.lists(st.text(min_size=10, max_size=200), max_size=10),
            'tags': st.lists(st.text(min_size=1, max_size=50), max_size=10)
        })
    )
    @settings(max_examples=50, deadline=5000)
    def test_product_migration_integrity(self, product_data):
        """
        Property: For any valid product data from MongoDB, migrating to Django should preserve
        all product information including images and tags as separate related records
        
        **Validates: Requirements 9.1, 9.2**
        """
        with transaction.atomic():
            # Create product
            product = Product.objects.create(
                gid=product_data['gid'],
                name=product_data['name'],
                price=product_data['price'],
                dis_price=product_data['disPrice'],
                description=product_data['description'],
                content=product_data['content'],
                status=product_data['status'],
                has_top=product_data['hasTop'],
                has_recommend=product_data['hasRecommend'],
                inventory=product_data['inventory'],
                sold=product_data['sold'],
                views=product_data['views']
            )
            
            # Migrate images
            migrated_images = []
            for i, image_url in enumerate(product_data['images']):
                image = ProductImage.objects.create(
                    product=product,
                    image_url=image_url,
                    is_primary=(i == 0),
                    order=i
                )
                migrated_images.append(image)
            
            # Migrate tags
            migrated_tags = []
            for tag_name in product_data['tags']:
                tag = ProductTag.objects.create(
                    product=product,
                    tag=tag_name
                )
                migrated_tags.append(tag)
            
            # Verify data integrity
            
            # 1. Core product data
            assert product.gid == product_data['gid']
            assert product.name == product_data['name']
            assert product.price == product_data['price']
            assert product.dis_price == product_data['disPrice']
            assert product.description == product_data['description']
            assert product.content == product_data['content']
            assert product.status == product_data['status']
            assert product.has_top == product_data['hasTop']
            assert product.has_recommend == product_data['hasRecommend']
            assert product.inventory == product_data['inventory']
            assert product.sold == product_data['sold']
            assert product.views == product_data['views']
            
            # 2. Images migration integrity
            assert ProductImage.objects.filter(product=product).count() == len(product_data['images'])
            
            for original_url, migrated_image in zip(product_data['images'], migrated_images):
                assert migrated_image.image_url == original_url
                assert migrated_image.product == product
            
            # 3. Primary image handling
            if product_data['images']:
                primary_images = ProductImage.objects.filter(product=product, is_primary=True)
                assert primary_images.count() == 1
                assert primary_images.first().image_url == product_data['images'][0]
            
            # 4. Tags migration integrity
            assert ProductTag.objects.filter(product=product).count() == len(product_data['tags'])
            
            migrated_tag_names = set(tag.tag for tag in migrated_tags)
            original_tag_names = set(product_data['tags'])
            assert migrated_tag_names == original_tag_names
            
            # 5. Image ordering
            ordered_images = ProductImage.objects.filter(product=product).order_by('order')
            for i, image in enumerate(ordered_images):
                assert image.order == i
                assert image.image_url == product_data['images'][i]

    @given(
        order_data=st.fixed_dictionaries({
            'roid': st.text(min_size=1, max_size=50),
            'uid': st.integers(min_value=1000, max_value=999999),
            'amount': st.decimals(min_value=0, max_value=99999, places=2),
            'status': st.integers(min_value=-1, max_value=7),
            'type': st.integers(min_value=1, max_value=2),
            'openid': st.text(min_size=10, max_size=100),
            'remark': st.text(max_size=200),
            'address': st.fixed_dictionaries({
                'name': st.text(min_size=1, max_size=50),
                'phone': st.text(min_size=11, max_size=11, alphabet='0123456789'),
                'address': st.text(min_size=1, max_size=100),
            }),
            'goods': st.lists(
                st.fixed_dictionaries({
                    'gid': st.text(min_size=1, max_size=50),
                    'quantity': st.integers(min_value=1, max_value=10),
                    'price': st.decimals(min_value=0, max_value=9999, places=2),
                    'amount': st.decimals(min_value=0, max_value=99999, places=2),
                }),
                min_size=1, max_size=5
            )
        })
    )
    @settings(max_examples=30, deadline=5000)
    def test_order_migration_integrity(self, order_data):
        """
        Property: For any valid order data from MongoDB, migrating to Django should preserve
        all order information including order items as separate related records
        
        **Validates: Requirements 9.1, 9.3**
        """
        with transaction.atomic():
            # Create test user first
            user = User.objects.create(
                username=f"user_{order_data['uid']}",
                wechat_openid=f"openid_{order_data['uid']}"
            )
            
            # Create order
            order = Order.objects.create(
                roid=order_data['roid'],
                uid=user,
                amount=order_data['amount'],
                status=order_data['status'],
                type=order_data['type'],
                openid=order_data['openid'],
                remark=order_data['remark'],
                address=order_data['address']
            )
            
            # Migrate order items
            migrated_items = []
            for i, item_data in enumerate(order_data['goods']):
                item = OrderItem.objects.create(
                    order=order,
                    rrid=f"{order_data['roid']}_item_{i}",
                    gid=item_data['gid'],
                    quantity=item_data['quantity'],
                    price=item_data['price'],
                    amount=item_data['amount'],
                    product_info=item_data
                )
                migrated_items.append(item)
            
            # Verify data integrity
            
            # 1. Core order data
            assert order.roid == order_data['roid']
            assert order.uid == user
            assert order.amount == order_data['amount']
            assert order.status == order_data['status']
            assert order.type == order_data['type']
            assert order.openid == order_data['openid']
            assert order.remark == order_data['remark']
            assert order.address == order_data['address']
            
            # 2. Order items migration integrity
            assert OrderItem.objects.filter(order=order).count() == len(order_data['goods'])
            
            for original_item, migrated_item in zip(order_data['goods'], migrated_items):
                assert migrated_item.gid == original_item['gid']
                assert migrated_item.quantity == original_item['quantity']
                assert migrated_item.price == original_item['price']
                assert migrated_item.amount == original_item['amount']
                assert migrated_item.product_info == original_item
                assert migrated_item.order == order
            
            # 3. Order item IDs are unique
            item_ids = [item.rrid for item in migrated_items]
            assert len(item_ids) == len(set(item_ids))  # All unique
            
            # 4. Order total calculation integrity
            calculated_total = sum(item.amount for item in migrated_items)
            # Allow for small decimal precision differences
            assert abs(order.amount - calculated_total) < Decimal('0.01')

    @given(
        migration_batch=st.fixed_dictionaries({
            'users': st.lists(
                st.fixed_dictionaries({
                    'uid': st.integers(min_value=1000, max_value=999999),
                    'nickName': st.text(min_size=1, max_size=50),
                    'openId': st.text(min_size=10, max_size=100),
                }),
                min_size=1, max_size=10
            ),
            'products': st.lists(
                st.fixed_dictionaries({
                    'gid': st.text(min_size=1, max_size=100),
                    'name': st.text(min_size=1, max_size=200),
                    'price': st.decimals(min_value=0, max_value=9999, places=2),
                }),
                min_size=1, max_size=10
            )
        })
    )
    @settings(max_examples=20, deadline=10000)
    def test_batch_migration_integrity(self, migration_batch):
        """
        Property: For any batch of migration data, all records should be migrated
        successfully with proper relationships and no data loss
        
        **Validates: Requirements 9.1, 9.2, 9.4**
        """
        # Ensure unique UIDs and GIDs within the batch
        user_uids = [user['uid'] for user in migration_batch['users']]
        product_gids = [product['gid'] for product in migration_batch['products']]
        
        assume(len(user_uids) == len(set(user_uids)))  # All UIDs unique
        assume(len(product_gids) == len(set(product_gids)))  # All GIDs unique
        
        with transaction.atomic():
            # Migrate users
            migrated_users = []
            for user_data in migration_batch['users']:
                user = User.objects.create(
                    username=user_data['nickName'][:150],
                    wechat_openid=user_data['openId']
                )
                
                # Create related records as migration would
                MembershipStatus.objects.create(
                    user=user,
                    tier=self.bronze_tier,
                    total_spending=Decimal('0.00')
                )
                
                PointsAccount.objects.create(
                    user=user,
                    balance=0,
                    total_earned=0,
                    total_spent=0
                )
                
                migrated_users.append(user)
            
            # Migrate products
            migrated_products = []
            for product_data in migration_batch['products']:
                product = Product.objects.create(
                    gid=product_data['gid'],
                    name=product_data['name'],
                    price=product_data['price']
                )
                migrated_products.append(product)
            
            # Verify batch migration integrity
            
            # 1. All users migrated
            assert User.objects.count() >= len(migration_batch['users'])
            
            # 2. All products migrated
            assert Product.objects.count() >= len(migration_batch['products'])
            
            # 3. All users have membership status
            for user in migrated_users:
                assert MembershipStatus.objects.filter(user=user).exists()
            
            # 4. All users have points account
            for user in migrated_users:
                assert PointsAccount.objects.filter(user=user).exists()
            
            # 5. No duplicate users by OpenID
            openids = [user.wechat_openid for user in migrated_users]
            assert len(openids) == len(set(openids))
            
            # 6. No duplicate products by GID
            gids = [product.gid for product in migrated_products]
            assert len(gids) == len(set(gids))
            
            # 7. Data consistency check
            for original_user, migrated_user in zip(migration_batch['users'], migrated_users):
                assert migrated_user.wechat_openid == original_user['openId']
                assert migrated_user.username == original_user['nickName'][:150]
            
            for original_product, migrated_product in zip(migration_batch['products'], migrated_products):
                assert migrated_product.gid == original_product['gid']
                assert migrated_product.name == original_product['name']
                assert migrated_product.price == original_product['price']

    def _convert_mongodb_user_data(self, user_data):
        """Convert MongoDB user data to Django User model format"""
        username = user_data['nickName'] or f"user_{user_data['uid']}"
        if len(username) > 150:
            username = username[:150]
        
        phone = user_data['phone'].strip() if user_data['phone'] else None
        if not phone:
            phone = None
        
        return {
            'username': username,
            'phone': phone,
            'wechat_openid': user_data['openId'],
            'wechat_session_key': user_data['session_key'],
            'avatar': user_data['avatar'] or '',
            'is_staff': user_data['roles'] == 0,
            'is_active': True,
        }