"""
Common validators for serializers across the application.

This module provides reusable validator functions that can be used
in DRF serializers to ensure consistent validation logic.
"""
import re
from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


def validate_phone(value):
    """
    Validate phone number format.
    
    Args:
        value: Phone number string
        
    Raises:
        serializers.ValidationError: If phone format is invalid
        
    Returns:
        str: Validated phone number
    """
    if not value:
        return value
    
    # Chinese phone number pattern: 11 digits starting with 1
    phone_pattern = re.compile(r'^1[3-9]\d{9}$')
    
    if not phone_pattern.match(value):
        raise serializers.ValidationError("Invalid phone number format. Expected: 11 digits starting with 1.")
    
    return value


def validate_phone_unique(value, exclude_user=None):
    """
    Validate phone number uniqueness.
    
    Args:
        value: Phone number string
        exclude_user: User instance to exclude from uniqueness check (for updates)
        
    Raises:
        serializers.ValidationError: If phone number already exists
        
    Returns:
        str: Validated phone number
    """
    if not value:
        return value
    
    queryset = User.objects.filter(phone=value)
    if exclude_user:
        queryset = queryset.exclude(pk=exclude_user.pk)
    
    if queryset.exists():
        raise serializers.ValidationError("Phone number already registered.")
    
    return value


def validate_email(value, exclude_user=None):
    """
    Validate email format and uniqueness.
    
    Args:
        value: Email string
        exclude_user: User instance to exclude from uniqueness check (for updates)
        
    Raises:
        serializers.ValidationError: If email format is invalid or already exists
        
    Returns:
        str: Validated email
    """
    if not value:
        return value
    
    # Basic email format validation
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    if not email_pattern.match(value):
        raise serializers.ValidationError("Invalid email format.")
    
    # Check uniqueness
    queryset = User.objects.filter(email=value)
    if exclude_user:
        queryset = queryset.exclude(pk=exclude_user.pk)
    
    if queryset.exists():
        raise serializers.ValidationError("Email already registered.")
    
    return value


def validate_password_strength(value):
    """
    Validate password strength.
    
    Requirements:
    - Minimum 6 characters
    - At least one letter and one number (recommended)
    
    Args:
        value: Password string
        
    Raises:
        serializers.ValidationError: If password doesn't meet strength requirements
        
    Returns:
        str: Validated password
    """
    if not value:
        raise serializers.ValidationError("Password cannot be empty.")
    
    if len(value) < 6:
        raise serializers.ValidationError("Password must be at least 6 characters long.")
    
    # Optional: Check for at least one letter and one number
    has_letter = re.search(r'[a-zA-Z]', value)
    has_number = re.search(r'\d', value)
    
    if not has_letter or not has_number:
        # Warning only, not required for basic validation
        pass
    
    return value


def validate_points_amount(value):
    """
    Validate points amount (must be multiple of 100).
    
    Args:
        value: Points amount integer
        
    Raises:
        serializers.ValidationError: If points amount is not a multiple of 100
        
    Returns:
        int: Validated points amount
    """
    if value % 100 != 0:
        raise serializers.ValidationError("Points must be in multiples of 100.")
    
    if value <= 0:
        raise serializers.ValidationError("Points amount must be greater than 0.")
    
    return value


def validate_price_range(value, min_value=0, max_value=None):
    """
    Validate price is within acceptable range.
    
    Args:
        value: Price decimal
        min_value: Minimum allowed price (default: 0)
        max_value: Maximum allowed price (optional)
        
    Raises:
        serializers.ValidationError: If price is outside valid range
        
    Returns:
        decimal.Decimal: Validated price
    """
    from decimal import Decimal
    
    if value < min_value:
        raise serializers.ValidationError(f"Price must be at least {min_value}.")
    
    if max_value is not None and value > max_value:
        raise serializers.ValidationError(f"Price must not exceed {max_value}.")
    
    return value


def validate_quantity(value, min_value=1):
    """
    Validate quantity is positive and meets minimum requirement.
    
    Args:
        value: Quantity integer
        min_value: Minimum allowed quantity (default: 1)
        
    Raises:
        serializers.ValidationError: If quantity is invalid
        
    Returns:
        int: Validated quantity
    """
    if value < min_value:
        raise serializers.ValidationError(f"Quantity must be at least {min_value}.")
    
    return value


def validate_discount_price(dis_price, price):
    """
    Validate discount price is less than original price.
    
    This is an object-level validator that should be used in validate() method.
    
    Args:
        dis_price: Discount price decimal
        price: Original price decimal
        
    Raises:
        serializers.ValidationError: If discount price is invalid
        
    Returns:
        decimal.Decimal: Validated discount price
    """
    if dis_price and price:
        if dis_price >= price:
            raise serializers.ValidationError({
                'dis_price': 'Discount price must be less than original price.'
            })
    
    return dis_price

