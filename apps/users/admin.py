from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Address


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin"""
    list_display = ['username', 'email', 'phone', 'wechat_openid', 'is_staff', 'created_at']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'created_at']
    search_fields = ['username', 'email', 'phone', 'wechat_openid']
    ordering = ['-created_at']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('WeChat Info', {'fields': ('phone', 'wechat_openid', 'wechat_session_key', 'avatar')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """Address admin"""
    list_display = ['user', 'name', 'phone', 'address', 'address_type', 'is_default', 'created_at']
    list_filter = ['address_type', 'is_default', 'created_at']
    search_fields = ['user__username', 'name', 'phone', 'address']
    ordering = ['-created_at']