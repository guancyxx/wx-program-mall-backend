"""
Price and quantity validators.
"""
from rest_framework import serializers
from decimal import Decimal


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

