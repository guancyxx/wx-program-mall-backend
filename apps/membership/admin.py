from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import MembershipTier, MembershipStatus, TierUpgradeLog


@admin.register(MembershipTier)
class MembershipTierAdmin(admin.ModelAdmin):
    """Admin interface for membership tiers"""
    
    list_display = [
        'display_name', 'name', 'min_spending', 'max_spending', 
        'points_multiplier', 'member_count', 'created_at'
    ]
    list_filter = ['name', 'created_at']
    search_fields = ['name', 'display_name']
    ordering = ['min_spending']
    readonly_fields = ['created_at', 'updated_at', 'member_count']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'display_name')
        }),
        ('Spending Thresholds', {
            'fields': ('min_spending', 'max_spending')
        }),
        ('Benefits', {
            'fields': ('points_multiplier', 'benefits')
        }),
        ('Statistics', {
            'fields': ('member_count',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def member_count(self, obj):
        """Count of members in this tier"""
        count = obj.membershipstatus_set.count()
        if count > 0:
            url = reverse('admin:membership_membershipstatus_changelist')
            return format_html(
                '<a href="{}?tier__id__exact={}">{} members</a>',
                url, obj.id, count
            )
        return '0 members'
    member_count.short_description = 'Members'
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of tiers that have members
        if obj and obj.membershipstatus_set.exists():
            return False
        return super().has_delete_permission(request, obj)


@admin.register(MembershipStatus)
class MembershipStatusAdmin(admin.ModelAdmin):
    """Admin interface for membership status"""
    
    list_display = [
        'user_link', 'tier', 'total_spending', 'tier_start_date', 
        'spending_to_next_tier', 'created_at'
    ]
    list_filter = ['tier', 'tier_start_date', 'created_at']
    search_fields = ['user__username', 'user__email', 'user__phone']
    ordering = ['-total_spending']
    readonly_fields = ['created_at', 'updated_at', 'spending_to_next_tier', 'tier_benefits', 'tier_start_date']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'tier')
        }),
        ('Spending & Progress', {
            'fields': ('total_spending', 'spending_to_next_tier', 'tier_start_date')
        }),
        ('Benefits', {
            'fields': ('tier_benefits',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_link(self, obj):
        """Link to user admin page"""
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'
    
    def spending_to_next_tier(self, obj):
        """Calculate spending needed for next tier"""
        current_tier = obj.tier
        next_tier = MembershipTier.objects.filter(
            min_spending__gt=current_tier.min_spending
        ).order_by('min_spending').first()
        
        if next_tier:
            needed = next_tier.min_spending - obj.total_spending
            if needed > 0:
                return format_html(
                    '${:.2f} to reach <strong>{}</strong>',
                    needed, next_tier.display_name
                )
            else:
                return format_html(
                    '<span style="color: green;">Eligible for {}</span>',
                    next_tier.display_name
                )
        return 'Highest tier reached'
    spending_to_next_tier.short_description = 'Next Tier Progress'
    
    def tier_benefits(self, obj):
        """Display tier benefits in a readable format"""
        benefits = obj.get_tier_benefits()
        if not benefits:
            return 'No benefits configured'
        
        html = '<ul>'
        for key, value in benefits.items():
            html += f'<li><strong>{key}:</strong> {value}</li>'
        html += '</ul>'
        return mark_safe(html)
    tier_benefits.short_description = 'Current Benefits'
    
    def get_queryset(self, request):
        """Optimize queryset with related objects"""
        return super().get_queryset(request).select_related('user', 'tier')
    
    actions = ['upgrade_to_next_tier', 'reset_spending']
    
    def upgrade_to_next_tier(self, request, queryset):
        """Admin action to manually upgrade selected members to next tier"""
        upgraded_count = 0
        for membership in queryset:
            current_tier = membership.tier
            next_tier = MembershipTier.objects.filter(
                min_spending__gt=current_tier.min_spending
            ).order_by('min_spending').first()
            
            if next_tier:
                membership.upgrade_tier(next_tier, "Manual admin upgrade")
                membership.save()
                upgraded_count += 1
        
        self.message_user(
            request,
            f'Successfully upgraded {upgraded_count} members to next tier.'
        )
    upgrade_to_next_tier.short_description = 'Upgrade selected members to next tier'
    
    def reset_spending(self, request, queryset):
        """Admin action to reset spending for selected members"""
        reset_count = 0
        for membership in queryset:
            membership.total_spending = 0
            # Downgrade to Bronze tier
            bronze_tier = MembershipTier.get_bronze_tier()
            if bronze_tier and membership.tier != bronze_tier:
                membership.upgrade_tier(bronze_tier, "Admin spending reset")
            membership.save()
            reset_count += 1
        
        self.message_user(
            request,
            f'Successfully reset spending for {reset_count} members.'
        )
    reset_spending.short_description = 'Reset spending for selected members'


@admin.register(TierUpgradeLog)
class TierUpgradeLogAdmin(admin.ModelAdmin):
    """Admin interface for tier upgrade logs"""
    
    list_display = [
        'user_link', 'from_tier', 'to_tier', 'reason', 
        'spending_amount', 'created_at'
    ]
    list_filter = ['from_tier', 'to_tier', 'created_at']
    search_fields = ['user__username', 'user__email', 'reason']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Upgrade Information', {
            'fields': ('user', 'from_tier', 'to_tier', 'reason')
        }),
        ('Details', {
            'fields': ('spending_amount', 'created_at')
        }),
    )
    
    def user_link(self, obj):
        """Link to user admin page"""
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'
    
    def get_queryset(self, request):
        """Optimize queryset with related objects"""
        return super().get_queryset(request).select_related('user', 'from_tier', 'to_tier')
    
    def has_add_permission(self, request):
        # Upgrade logs are created automatically
        return False
    
    def has_change_permission(self, request, obj=None):
        # Upgrade logs should not be modified
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Allow deletion for cleanup purposes, but only for superusers
        return request.user.is_superuser