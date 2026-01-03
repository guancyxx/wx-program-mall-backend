from django.contrib import admin
from .models import PointsAccount, PointsRule, PointsTransaction, PointsExpiration


@admin.register(PointsAccount)
class PointsAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'available_points', 'total_points', 'lifetime_earned', 'lifetime_redeemed', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username', 'user__email', 'user__phone']
    readonly_fields = ['total_points', 'lifetime_earned', 'lifetime_redeemed', 'created_at', 'updated_at']
    
    def has_add_permission(self, request):
        return False  # Points accounts are created automatically


@admin.register(PointsRule)
class PointsRuleAdmin(admin.ModelAdmin):
    list_display = ['rule_type', 'points_amount', 'is_percentage', 'is_active', 'created_at']
    list_filter = ['rule_type', 'is_percentage', 'is_active', 'created_at']
    search_fields = ['rule_type', 'description']
    list_editable = ['is_active']


@admin.register(PointsTransaction)
class PointsTransactionAdmin(admin.ModelAdmin):
    list_display = ['account', 'transaction_type', 'amount', 'balance_after', 'description', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['account__user__username', 'description', 'reference_id']
    readonly_fields = ['created_at']
    
    def has_add_permission(self, request):
        return False  # Transactions are created programmatically
    
    def has_change_permission(self, request, obj=None):
        return False  # Transactions should not be modified


@admin.register(PointsExpiration)
class PointsExpirationAdmin(admin.ModelAdmin):
    list_display = ['account', 'points_amount', 'remaining_points', 'earned_date', 'expiry_date', 'is_expired', 'is_fully_redeemed']
    list_filter = ['is_expired', 'is_fully_redeemed', 'earned_date', 'expiry_date']
    search_fields = ['account__user__username']
    readonly_fields = ['points_amount', 'earned_date', 'expiry_date', 'transaction', 'created_at']
    
    def has_add_permission(self, request):
        return False  # Expiration records are created automatically