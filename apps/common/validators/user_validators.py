"""
User-related validators for phone, email, and password validation.
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


