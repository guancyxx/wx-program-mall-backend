"""
User serializers for list, detail, registration, and update operations.
"""
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from apps.common.validators import (
    validate_phone, validate_phone_unique, validate_email,
    validate_password_strength
)
from ..models import User


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
            # avatar is now a URL string, not an ImageField
            return obj.avatar
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
            'avatar', 'avatar_url', 'wechat_openid', 'is_staff', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'wechat_openid', 'is_staff', 'created_at', 'updated_at']

    def get_avatar_url(self, obj):
        """Get full avatar URL"""
        if obj.avatar:
            # avatar is now a URL string, not an ImageField
            return obj.avatar
        return None


class UserInfoSerializer(serializers.ModelSerializer):
    """
    Serializer for getUserInfo endpoint - matches Node.js API format.
    Used for: GET /api/users/getUserInfo/
    Returns fields in camelCase format expected by frontend.
    """
    uid = serializers.IntegerField(source='id', read_only=True)
    nickName = serializers.CharField(source='first_name', read_only=True)
    avatar = serializers.SerializerMethodField()
    token = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    is_staff = serializers.SerializerMethodField()  # 使用 SerializerMethodField 确保正确处理
    createTime = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'uid', 'nickName', 'avatar', 'token', 'roles', 'is_staff', 
            'createTime', 'address'
        ]
        read_only_fields = fields
    
    def get_avatar(self, obj):
        """Get avatar URL"""
        if obj.avatar:
            # avatar is now a URL string, not an ImageField
            return obj.avatar
        return ''
    
    def get_token(self, obj):
        """Get JWT token from request"""
        request = self.context.get('request')
        if request and hasattr(request, 'auth') and request.auth:
            return str(request.auth)
        return ''
    
    def get_roles(self, obj):
        """Get roles - 0 for staff, 1 for normal user"""
        return 0 if obj.is_staff else 1
    
    def get_is_staff(self, obj):
        """Get is_staff - ensure it's always a boolean"""
        return bool(obj.is_staff) if obj.is_staff is not None else False
    
    def get_createTime(self, obj):
        """Convert created_at to timestamp (milliseconds)"""
        if obj.created_at:
            return int(obj.created_at.timestamp() * 1000)
        return None
    
    def get_address(self, obj):
        """Get user addresses"""
        # Import here to avoid circular imports
        from ..models import Address
        addresses = Address.objects.filter(user=obj)
        return [
            {
                'id': addr.id,
                'name': addr.name,
                'phone': addr.phone,
                'address': addr.address,
                'detail': addr.detail,
                'address_type': addr.address_type,
                'is_default': addr.is_default
            }
            for addr in addresses
        ]


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
        
        # Ensure first_name and last_name are never None (use empty string if not provided)
        if 'first_name' not in validated_data:
            validated_data['first_name'] = ''
        elif validated_data.get('first_name') is None:
            validated_data['first_name'] = ''
        
        if 'last_name' not in validated_data:
            validated_data['last_name'] = ''
        elif validated_data.get('last_name') is None:
            validated_data['last_name'] = ''
        
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
    # Explicitly define avatar as URLField to override any model field inference
    avatar = serializers.URLField(required=False, allow_blank=True, allow_null=True, max_length=500, help_text="Avatar URL from cloud storage")

    class Meta:
        model = User
        fields = [
            'username', 'email', 'phone', 'first_name', 'last_name', 'avatar'
        ]
        # Explicitly specify that avatar should be treated as URLField, not file field
        extra_kwargs = {
            'avatar': {'required': False, 'allow_blank': True, 'allow_null': True}
        }

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

    def validate_avatar(self, value):
        """Validate avatar URL"""
        # Allow empty string or null
        if not value:
            return value
        # URLField already validates URL format, so just return the value
        return value
