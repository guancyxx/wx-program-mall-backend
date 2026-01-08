from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from apps.common.validators import (
    validate_phone, validate_phone_unique, validate_email,
    validate_password_strength
)
from .models import User, Address


class UserListSerializer(serializers.ModelSerializer):
    """
    Serializer for user list view - minimal fields for list display.
    Used for: GET /api/users/
    """
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'avatar_url', 'created_at']
        read_only_fields = fields

    def get_avatar_url(self, obj):
        """Get full avatar URL"""
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for user detail view - complete fields for detail display.
    Used for: GET /api/users/{id}/
    Note: Does not include sensitive fields like password or wechat_session_key.
    """
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'first_name', 'last_name', 
            'avatar', 'avatar_url', 'wechat_openid', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'wechat_openid', 'created_at', 'updated_at']

    def get_avatar_url(self, obj):
        """Get full avatar URL"""
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration (create operation).
    Used for: POST /api/users/register/
    """
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password_strength],
        help_text="Password must be at least 6 characters long"
    )
    confirm_password = serializers.CharField(write_only=True)
    phone = serializers.CharField(
        required=False,
        allow_blank=True,
        validators=[validate_phone],
        help_text="Phone number (11 digits starting with 1)"
    )
    email = serializers.EmailField(
        validators=[lambda v: validate_email(v, exclude_user=None)],
        help_text="Email address"
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'phone', 'password', 'confirm_password', 
            'first_name', 'last_name'
        ]

    def validate(self, attrs):
        """Object-level validation: check password confirmation"""
        if attrs.get('password') != attrs.get('confirm_password'):
            raise serializers.ValidationError({
                'confirm_password': "Passwords don't match"
            })
        return attrs

    def validate_phone(self, value):
        """Validate phone uniqueness during registration"""
        if value:
            return validate_phone_unique(value, exclude_user=None)
        return value

    def validate_email(self, value):
        """Validate email uniqueness during registration"""
        return validate_email(value, exclude_user=None)

    def create(self, validated_data):
        """Create user with hashed password"""
        validated_data.pop('confirm_password')
        validated_data['password'] = make_password(validated_data['password'])
        return User.objects.create(**validated_data)


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for user update operation.
    Used for: PUT/PATCH /api/users/{id}/
    Supports partial updates and validates email uniqueness on update.
    """
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(
        required=False,
        allow_blank=True,
        validators=[validate_phone],
        help_text="Phone number (11 digits starting with 1)"
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'phone', 'first_name', 'last_name', 'avatar'
        ]

    def validate_email(self, value):
        """Validate email uniqueness, excluding current user"""
        if value and self.instance:
            return validate_email(value, exclude_user=self.instance)
        return value

    def validate_phone(self, value):
        """Validate phone uniqueness, excluding current user"""
        if value and self.instance:
            return validate_phone_unique(value, exclude_user=self.instance)
        return value


class AddressSerializer(serializers.ModelSerializer):
    """Address serializer"""
    
    class Meta:
        model = Address
        fields = ['id', 'name', 'phone', 'address', 'detail', 'address_type', 
                 'is_default', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']