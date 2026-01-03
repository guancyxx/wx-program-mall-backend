#!/usr/bin/env python
"""
Development database setup script for Mall Server.
This script creates the development database and sets up initial data.
"""

import os
import sys
import django
import pymysql
from decouple import config

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mall_server.settings.development')
django.setup()

def create_database():
    """Create the development database if it doesn't exist."""
    try:
        # Database connection parameters
        db_config = {
            'host': config('MYSQL_HOST', default='localhost'),
            'port': int(config('MYSQL_PORT', default='3306')),
            'user': config('MYSQL_USER', default='root'),
            'password': config('MYSQL_PASSWORD', default='dev_password'),
            'charset': 'utf8mb4'
        }
        
        db_name = config('MYSQL_DATABASE', default='mall_server_dev')
        
        print(f"Connecting to MySQL server at {db_config['host']}:{db_config['port']}...")
        
        # Connect to MySQL server (without specifying database)
        connection = pymysql.connect(**db_config)
        
        try:
            with connection.cursor() as cursor:
                # Create database if it doesn't exist
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                print(f"Database '{db_name}' created or already exists.")
                
                # Grant privileges (if needed)
                cursor.execute(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_config['user']}'@'%'")
                cursor.execute("FLUSH PRIVILEGES")
                print(f"Privileges granted to user '{db_config['user']}'.")
                
            connection.commit()
            
        finally:
            connection.close()
            
        print("Database setup completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error setting up database: {e}")
        return False

def run_migrations():
    """Run Django migrations."""
    try:
        print("Running Django migrations...")
        from django.core.management import execute_from_command_line
        
        # Make migrations
        execute_from_command_line(['manage.py', 'makemigrations'])
        
        # Apply migrations
        execute_from_command_line(['manage.py', 'migrate'])
        
        print("Migrations completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error running migrations: {e}")
        return False

def create_superuser():
    """Create a superuser for development."""
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Check if superuser already exists
        if User.objects.filter(is_superuser=True).exists():
            print("Superuser already exists.")
            return True
            
        # Create superuser
        admin_phone = config('ADMIN_PHONE', default='13800000000')
        admin_password = config('ADMIN_PASSWORD', default='admin123456')
        admin_nickname = config('ADMIN_NICKNAME', default='系统管理员')
        
        user = User.objects.create_superuser(
            username=admin_phone,
            phone=admin_phone,
            password=admin_password,
            nickname=admin_nickname,
            is_staff=True,
            is_superuser=True
        )
        
        print(f"Superuser created: {admin_phone}")
        return True
        
    except Exception as e:
        print(f"Error creating superuser: {e}")
        return False

def main():
    """Main setup function."""
    print("=== Mall Server Development Database Setup ===")
    
    # Step 1: Create database
    if not create_database():
        print("Failed to create database. Exiting.")
        sys.exit(1)
    
    # Step 2: Run migrations
    if not run_migrations():
        print("Failed to run migrations. Exiting.")
        sys.exit(1)
    
    # Step 3: Create superuser
    if not create_superuser():
        print("Failed to create superuser. Continuing...")
    
    print("\n=== Setup completed successfully! ===")
    print("You can now start the development server with:")
    print("python manage.py runserver --settings=mall_server.settings.development")

if __name__ == '__main__':
    main()