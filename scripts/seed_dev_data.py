#!/usr/bin/env python
"""
Development data seeding script.
This script creates sample data for development and testing.
"""
import os
import sys
import django
from pathlib import Path
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mall_server.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from apps.membership.models import MembershipTier, MembershipStatus
from apps.products.models import Category, Product
from apps.points.models import PointsAccount, PointsRule

User = get_user_model()


def create_sample_users():
    """Create sample users with different membership tiers."""
    print("Creating sample users...")
    
    users_data = [
        {
            'username': 'bronze_user',
            'email': 'bronze@example.com',
            'password': 'password123',
            'tier': 'bronze',
            'spending': 500
        },
        {
            'username': 'silver_user',
            'email': 'silver@example.com',
            'password': 'password123',
            'tier': 'silver',
            'spending': 2500
        },
        {
            'username': 'gold_user',
            'email': 'gold@example.com',
            'password': 'password123',
            'tier': 'gold',
            'spending': 10000
        },
        {
            'username': 'platinum_user',
            'email': 'platinum@example.com',
            'password': 'password123',
            'tier': 'platinum',
            'spending': 50000
        }
    ]
    
    for user_data in users_data:
        user, created = User.objects.get_or_create(
            username=user_data['username'],
            defaults={
                'email': user_data['email'],
                'first_name': user_data['username'].replace('_', ' ').title(),
            }
        )
        
        if created:
            user.set_password(user_data['password'])
            user.save()
            
            # Update membership status
            try:
                membership = user.membership
                tier = MembershipTier.objects.get(name=user_data['tier'])
                membership.tier = tier
                membership.total_spending = Decimal(str(user_data['spending']))
                membership.save()
                
                print(f"✓ Created {user_data['tier']} user: {user.username}")
            except Exception as e:
                print(f"✗ Error updating membership for {user.username}: {e}")
        else:
            print(f"✓ User {user.username} already exists")


def create_sample_categories():
    """Create sample product categories."""
    print("Creating sample categories...")
    
    categories_data = [
        {'name': 'Electronics', 'description': 'Electronic devices and gadgets'},
        {'name': 'Clothing', 'description': 'Fashion and apparel'},
        {'name': 'Books', 'description': 'Books and educational materials'},
        {'name': 'Home & Garden', 'description': 'Home improvement and garden supplies'},
        {'name': 'Sports', 'description': 'Sports equipment and accessories'},
    ]
    
    for cat_data in categories_data:
        category, created = Category.objects.get_or_create(
            name=cat_data['name'],
            defaults=cat_data
        )
        
        if created:
            print(f"✓ Created category: {category.name}")
        else:
            print(f"✓ Category {category.name} already exists")


def create_sample_products():
    """Create sample products."""
    print("Creating sample products...")
    
    # Get categories
    electronics = Category.objects.get(name='Electronics')
    clothing = Category.objects.get(name='Clothing')
    books = Category.objects.get(name='Books')
    
    products_data = [
        {
            'name': 'Smartphone Pro Max',
            'description': 'Latest flagship smartphone with advanced features',
            'price': Decimal('999.99'),
            'discount_price': Decimal('899.99'),
            'category': electronics,
            'is_featured': True,
            'stock_quantity': 50
        },
        {
            'name': 'Wireless Headphones',
            'description': 'Premium noise-cancelling wireless headphones',
            'price': Decimal('299.99'),
            'category': electronics,
            'stock_quantity': 100
        },
        {
            'name': 'Designer T-Shirt',
            'description': 'Premium cotton t-shirt with modern design',
            'price': Decimal('49.99'),
            'category': clothing,
            'stock_quantity': 200
        },
        {
            'name': 'Programming Guide',
            'description': 'Comprehensive guide to modern programming',
            'price': Decimal('39.99'),
            'category': books,
            'is_member_exclusive': True,
            'stock_quantity': 75
        },
        {
            'name': 'Laptop Stand',
            'description': 'Ergonomic adjustable laptop stand',
            'price': Decimal('79.99'),
            'discount_price': Decimal('59.99'),
            'category': electronics,
            'stock_quantity': 30
        }
    ]
    
    for prod_data in products_data:
        product, created = Product.objects.get_or_create(
            name=prod_data['name'],
            defaults=prod_data
        )
        
        if created:
            print(f"✓ Created product: {product.name}")
        else:
            print(f"✓ Product {product.name} already exists")


def award_sample_points():
    """Award some points to sample users."""
    print("Awarding sample points...")
    
    try:
        # Award points to users
        users = User.objects.filter(username__in=['bronze_user', 'silver_user', 'gold_user', 'platinum_user'])
        
        for user in users:
            try:
                points_account = user.points_account
                
                # Award registration bonus if not already awarded
                if points_account.lifetime_earned == 0:
                    points_account.add_points(
                        amount=100,
                        transaction_type='earning',
                        description='Registration bonus'
                    )
                    print(f"✓ Awarded registration bonus to {user.username}")
                
            except Exception as e:
                print(f"✗ Error awarding points to {user.username}: {e}")
                
    except Exception as e:
        print(f"✗ Error in points awarding: {e}")


def main():
    """Main seeding function."""
    print("🌱 Seeding development data...")
    print("=" * 50)
    
    try:
        create_sample_users()
        create_sample_categories()
        create_sample_products()
        award_sample_points()
        
        print("=" * 50)
        print("🎉 Development data seeding completed successfully!")
        print("\nSample users created:")
        print("- bronze_user / password123 (Bronze tier)")
        print("- silver_user / password123 (Silver tier)")
        print("- gold_user / password123 (Gold tier)")
        print("- platinum_user / password123 (Platinum tier)")
        
    except Exception as e:
        print(f"✗ Error during seeding: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()