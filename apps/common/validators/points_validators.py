"""
Points-related validators.
"""
from rest_framework import serializers


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




