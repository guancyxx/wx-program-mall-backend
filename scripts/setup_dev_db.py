#!/usr/bin/env python
"""
Development database setup script.
This script sets up the development database with initial data.
"""
import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mall_server.settings.development')
django.setup()

from django.core.management import execute_from_command_line
from django.db import connection
from django.conf import settings
import pymysql


def create_database_if_not_exists():
    """Create the database if it doesn't exist."""
    db_config = settings.DATABASES['default']
    db_name = db_config['NAME']
    
    # Connect to MySQL without specifying database
    connection_params = {
        'host': db_config['HOST'],
        'port': int(db_config['PORT']),
        'user': db_config['USER'],
        'password': db_config['PASSWORD'],
        'charset': 'utf8mb4'
    }
    
    try:
        conn = pymysql.connect(**connection_params)
        cursor = conn.cursor()
        
        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✓ Database '{db_name}' created or already exists")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Error creating database: {e}")
        print("Please ensure MySQL/MariaDB is running and credentials are correct")
        return False
    
    return True


def run_migrations():
    """Run Django migrations."""
    print("Running migrations...")
    try:
        execute_from_command_line(['manage.py', 'migrate'])
        print("✓ Migrations completed successfully")
        return True
    except Exception as e:
        print(f"✗ Error running migrations: {e}")
        return False


def setup_initial_data():
    """Set up initial data using management command."""
    print("Setting up initial data...")
    try:
        execute_from_command_line(['manage.py', 'setup_test_data'])
        print("✓ Initial data setup completed")
        return True
    except Exception as e:
        print(f"✗ Error setting up initial data: {e}")
        return False


def create_superuser():
    """Create a superuser for development."""
    print("Creating superuser...")
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            print("✓ Superuser 'admin' created (password: admin123)")
        else:
            print("✓ Superuser 'admin' already exists")
        
        return True
    except Exception as e:
        print(f"✗ Error creating superuser: {e}")
        return False


def main():
    """Main setup function."""
    print("🚀 Setting up development database...")
    print("=" * 50)
    
    # Step 1: Create database
    if not create_database_if_not_exists():
        sys.exit(1)
    
    # Step 2: Run migrations
    if not run_migrations():
        sys.exit(1)
    
    # Step 3: Set up initial data
    if not setup_initial_data():
        sys.exit(1)
    
    # Step 4: Create superuser
    if not create_superuser():
        sys.exit(1)
    
    print("=" * 50)
    print("🎉 Development database setup completed successfully!")
    print("\nNext steps:")
    print("1. Start the development server: python manage.py runserver")
    print("2. Access admin panel: http://localhost:8000/admin/")
    print("3. Login with: admin / admin123")


if __name__ == '__main__':
    main()