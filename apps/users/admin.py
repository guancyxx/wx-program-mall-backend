from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User, Address


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin with enhanced features"""
    list_display = [
        'username', 'email', 'phone', 'wechat_openid', 
        'membership_tier', 'total_spending', 'is_staff', 'created_at'
    ]
    list_filter = [
        'is_staff', 'is_superuser', 'is_active', 'created_at',
        'membership__tier'
    ]
    search_fields = ['username', 'email', 'phone', 'wechat_openid']
    ordering = ['-created_at']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('WeChat Info', {
            'fields': ('phone', 'wechat_openid', 'wechat_session_key', 'avatar_preview')
        }),
        ('Membership Info', {
            'fields': ('membership_info', 'points_balance'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = [
        'created_at', 'updated_at', 'avatar_preview', 
        'membership_info', 'points_balance'
    ]
    
    def membership_tier(self, obj):
        """Display user's membership tier with link"""
        try:
            membership = obj.membership
            url = reverse('admin:membership_membershipstatus_change', args=[membership.id])
            return format_html(
                '<a href="{}" style="color: {};">{}</a>',
                url,
                self._get_tier_color(membership.tier.name),
                membership.tier.display_name
            )
        except:
            return 'No membership'
    membership_tier.short_description = 'Tier'
    membership_tier.admin_order_field = 'membership__tier__name'
    
    def total_spending(self, obj):
        """Display user's total spending"""
        try:
            return f"${obj.membership.total_spending:.2f}"
        except:
            return '$0.00'
    total_spending.short_description = 'Total Spending'
    total_spending.admin_order_field = 'membership__total_spending'
    
    def avatar_preview(self, obj):
        """Display avatar preview"""
        if obj.avatar:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 50%;" />',
                obj.avatar.url
            )
        return 'No avatar'
    avatar_preview.short_description = 'Avatar'
    
    def membership_info(self, obj):
        """Display detailed membership information"""
        try:
            membership = obj.membership
            html = f"""
            <div>
                <strong>Tier:</strong> {membership.tier.display_name}<br>
                <strong>Total Spending:</strong> ${membership.total_spending:.2f}<br>
                <strong>Tier Since:</strong> {membership.tier_start_date.strftime('%Y-%m-%d')}<br>
                <strong>Points Multiplier:</strong> {membership.tier.points_multiplier}x
            </div>
            """
            return mark_safe(html)
        except:
            return 'No membership information'
    membership_info.short_description = 'Membership Details'
    
    def points_balance(self, obj):
        """Display user's points balance"""
        try:
            points_account = obj.points_account
            return f"{points_account.available_points:,} points"
        except:
            return '0 points'
    points_balance.short_description = 'Points Balance'
    
    def _get_tier_color(self, tier_name):
        """Get color for tier display"""
        colors = {
            'bronze': '#CD7F32',
            'silver': '#C0C0C0',
            'gold': '#FFD700',
            'platinum': '#E5E4E2'
        }
        return colors.get(tier_name, '#000000')
    
    def get_queryset(self, request):
        """Optimize queryset with related objects"""
        return super().get_queryset(request).select_related(
            'membership', 'membership__tier'
        ).prefetch_related('points_account')
    
    actions = ['activate_users', 'deactivate_users', 'reset_passwords']
    
    def activate_users(self, request, queryset):
        """Activate selected users"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} users activated.')
    activate_users.short_description = 'Activate selected users'
    
    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} users deactivated.')
    deactivate_users.short_description = 'Deactivate selected users'


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """Enhanced Address admin"""
    list_display = [
        'user_link', 'name', 'phone', 'address_short', 
        'address_type', 'is_default', 'created_at'
    ]
    list_filter = ['address_type', 'is_default', 'created_at']
    search_fields = ['user__username', 'name', 'phone', 'address']
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'name', 'phone')
        }),
        ('Address Details', {
            'fields': ('address', 'address_type', 'is_default')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    
    def user_link(self, obj):
        """Link to user admin page"""
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'
    
    def address_short(self, obj):
        """Display shortened address"""
        if len(obj.address) > 50:
            return obj.address[:50] + '...'
        return obj.address
    address_short.short_description = 'Address'
    
    def get_queryset(self, request):
        """Optimize queryset with related objects"""
        return super().get_queryset(request).select_related('user')
    
    actions = ['set_as_default', 'unset_default']
    
    def set_as_default(self, request, queryset):
        """Set selected addresses as default for their users"""
        updated_count = 0
        for address in queryset:
            # First unset all default addresses for this user
            Address.objects.filter(user=address.user, is_default=True).update(is_default=False)
            # Then set this address as default
            address.is_default = True
            address.save()
            updated_count += 1
        
        self.message_user(request, f'{updated_count} addresses set as default.')
    set_as_default.short_description = 'Set as default address'
    
    def unset_default(self, request, queryset):
        """Unset default status for selected addresses"""
        updated = queryset.update(is_default=False)
        self.message_user(request, f'{updated} addresses unset as default.')
    unset_default.short_description = 'Unset default status'