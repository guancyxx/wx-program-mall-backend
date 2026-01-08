#!/usr/bin/env python
"""
Script to fix corrupted password hashes with double dollar signs.
This addresses the "Invalid salt" error by fixing the hash format.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mall_server.settings')
django.setup()

from apps.users.models import User
from apps.common.password_utils import SecurePasswordHasher

def fix_corrupted_hashes():
    """Fix all users with corrupted password hashes (double $ format)."""
    
    print("Checking for users with corrupted password hashes...")
    
    # Find users with the old double $ format
    corrupted_users = User.objects.filter(password__startswith='secure_bcrypt$$')
    
    print(f"Found {corrupted_users.count()} users with corrupted hashes")
    
    if corrupted_users.count() == 0:
        print("No corrupted hashes found. All users are using the correct format.")
        return
    
    hasher = SecurePasswordHasher()
    
    for user in corrupted_users:
        print(f"Fixing user: {user.username}")
        
        # Extract the bcrypt hash part from the corrupted format
        old_hash = user.password
        if old_hash.startswith('secure_bcrypt$$'):
            bcrypt_part = old_hash[len('secure_bcrypt$$'):]
            # Create new hash in correct format
            new_hash = f"secure_bcrypt${bcrypt_part}"
            user.password = new_hash
            user.save()
            print(f"  ✓ Fixed hash format for {user.username}")
        else:
            print(f"  ⚠ Unexpected hash format for {user.username}: {old_hash[:30]}...")
    
    print(f"\nCompleted fixing {corrupted_users.count()} users")
    print("All users should now be able to authenticate properly.")

if __name__ == '__main__':
    fix_corrupted_hashes()