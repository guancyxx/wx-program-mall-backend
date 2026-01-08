from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from .models import AdminAuditLog, SystemConfiguration, SystemNotification, Store


class MallAdminSite(AdminSite):
    """Custom admin site for the mall system"""
    
    site_header = 'Mall Management System'
    site_title = 'Mall Admin'
    index_title = 'Welcome to Mall Administration'
    
    def index(self, request, extra_context=None):
        """Custom admin index with dashboard statistics"""
        extra_context = extra_context or {}
        
        # Get statistics
        try:
            from apps.users.models import User
            from apps.orders.models import Order
            from apps.products.models import Product
            from apps.membership.models import MembershipStatus, MembershipTier
            
            # User statistics
            total_users = User.objects.count()
            active_users = User.objects.filter(is_active=True).count()
            new_users_today = User.objects.filter(
                created_at__date=timezone.now().date()
            ).count()
            
            # Order statistics
            total_orders = Order.objects.count()
            orders_today = Order.objects.filter(
                create_time__date=timezone.now().date()
            ).count()
            pending_orders = Order.objects.filter(status=0).count()
            
            # Revenue statistics
            total_revenue = Order.objects.filter(
                status__in=[1, 2, 3, 4]  # Paid, Processing, Shipped, Delivered
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            revenue_today = Order.objects.filter(
                create_time__date=timezone.now().date(),
                status__in=[1, 2, 3, 4]
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Product statistics
            total_products = Product.objects.count()
            active_products = Product.objects.filter(status=1).count()
            low_stock_products = Product.objects.filter(inventory__lte=10).count()
            out_of_stock_products = Product.objects.filter(inventory=0).count()
            
            # Membership statistics
            membership_stats = MembershipTier.objects.annotate(
                member_count=Count('membershipstatus')
            ).values('display_name', 'member_count')
            
            extra_context.update({
                'dashboard_stats': {
                    'users': {
                        'total': total_users,
                        'active': active_users,
                        'new_today': new_users_today,
                    },
                    'orders': {
                        'total': total_orders,
                        'today': orders_today,
                        'pending': pending_orders,
                    },
                    'revenue': {
                        'total': total_revenue,
                        'today': revenue_today,
                    },
                    'products': {
                        'total': total_products,
                        'active': active_products,
                        'low_stock': low_stock_products,
                        'out_of_stock': out_of_stock_products,
                    },
                    'membership': list(membership_stats),
                }
            })
        except Exception as e:
            # If there's an error getting stats, just continue without them
            extra_context['dashboard_error'] = str(e)
        
        return super().index(request, extra_context)


# Create custom admin site instance
mall_admin_site = MallAdminSite(name='mall_admin')


@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    """Admin interface for audit logs"""
    
    list_display = [
        'user_link', 'action', 'model_name', 'object_repr', 
        'ip_address', 'created_at'
    ]
    list_filter = ['action', 'model_name', 'created_at']
    search_fields = ['user__username', 'model_name', 'object_repr', 'message']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('User & Action', {
            'fields': ('user', 'action', 'created_at')
        }),
        ('Object Information', {
            'fields': ('model_name', 'object_id', 'object_repr')
        }),
        ('Details', {
            'fields': ('message', 'ip_address', 'user_agent')
        }),
    )
    
    def user_link(self, obj):
        """Link to user admin page"""
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'
    
    def has_add_permission(self, request):
        # Audit logs are created automatically
        return False
    
    def has_change_permission(self, request, obj=None):
        # Audit logs should not be modified
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete audit logs
        return request.user.is_superuser


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    """Admin interface for system configurations"""
    
    list_display = ['key', 'value_preview', 'is_active', 'updated_by', 'updated_at']
    list_filter = ['is_active', 'updated_at']
    search_fields = ['key', 'value', 'description']
    ordering = ['key']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Configuration', {
            'fields': ('key', 'value', 'description', 'is_active')
        }),
        ('Metadata', {
            'fields': ('updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def value_preview(self, obj):
        """Show preview of value"""
        if len(obj.value) > 50:
            return obj.value[:50] + '...'
        return obj.value
    value_preview.short_description = 'Value'
    
    def save_model(self, request, obj, form, change):
        """Set updated_by field"""
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SystemNotification)
class SystemNotificationAdmin(admin.ModelAdmin):
    """Admin interface for system notifications"""
    
    list_display = [
        'title', 'notification_type', 'priority', 'is_read', 
        'is_active', 'target_count', 'created_at', 'expires_at'
    ]
    list_filter = [
        'notification_type', 'priority', 'is_read', 'is_active', 
        'created_at', 'expires_at'
    ]
    search_fields = ['title', 'message']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    filter_horizontal = ['target_users']
    
    fieldsets = (
        ('Notification Content', {
            'fields': ('title', 'message', 'notification_type', 'priority')
        }),
        ('Status & Targeting', {
            'fields': ('is_read', 'is_active', 'target_users')
        }),
        ('Timing', {
            'fields': ('created_at', 'expires_at')
        }),
    )
    
    def target_count(self, obj):
        """Count of target users"""
        count = obj.target_users.count()
        if count == 0:
            return 'All users'
        return f'{count} users'
    target_count.short_description = 'Targets'
    
    actions = ['mark_as_read', 'mark_as_unread', 'activate_notifications', 'deactivate_notifications']
    
    def mark_as_read(self, request, queryset):
        """Mark selected notifications as read"""
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} notifications marked as read.')
    mark_as_read.short_description = 'Mark as read'
    
    def mark_as_unread(self, request, queryset):
        """Mark selected notifications as unread"""
        updated = queryset.update(is_read=False)
        self.message_user(request, f'{updated} notifications marked as unread.')
    mark_as_unread.short_description = 'Mark as unread'
    
    def activate_notifications(self, request, queryset):
        """Activate selected notifications"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} notifications activated.')
    activate_notifications.short_description = 'Activate notifications'
    
    def deactivate_notifications(self, request, queryset):
        """Deactivate selected notifications"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} notifications deactivated.')
    deactivate_notifications.short_description = 'Deactivate notifications'


class BaseModelAdmin(admin.ModelAdmin):
    """Base admin class with common functionality"""
    
    def get_readonly_fields(self, request, obj=None):
        """Make created_at and updated_at fields readonly by default"""
        readonly_fields = list(super().get_readonly_fields(request, obj))
        
        # Add common timestamp fields if they exist
        if hasattr(self.model, 'created_at') and 'created_at' not in readonly_fields:
            readonly_fields.append('created_at')
        if hasattr(self.model, 'updated_at') and 'updated_at' not in readonly_fields:
            readonly_fields.append('updated_at')
        
        return readonly_fields
    
    def save_model(self, request, obj, form, change):
        """Add user tracking for model saves"""
        if not change:  # Creating new object
            if hasattr(obj, 'created_by') and not obj.created_by:
                obj.created_by = request.user
        
        if hasattr(obj, 'updated_by'):
            obj.updated_by = request.user
        
        super().save_model(request, obj, form, change)


class AdminPermissionMixin:
    """Mixin to add permission checks for admin actions"""
    
    def has_view_permission(self, request, obj=None):
        """Check view permission"""
        return request.user.is_staff and super().has_view_permission(request, obj)
    
    def has_add_permission(self, request):
        """Check add permission"""
        return request.user.is_staff and super().has_add_permission(request)
    
    def has_change_permission(self, request, obj=None):
        """Check change permission"""
        return request.user.is_staff and super().has_change_permission(request, obj)
    
    def has_delete_permission(self, request, obj=None):
        """Check delete permission - require superuser for sensitive models"""
        sensitive_models = ['User', 'Order', 'PaymentTransaction']
        
        if self.model.__name__ in sensitive_models:
            return request.user.is_superuser
        
        return request.user.is_staff and super().has_delete_permission(request, obj)


class AuditLogMixin:
    """Mixin to add audit logging for admin actions"""
    
    def log_addition(self, request, object, message):
        """Log object addition"""
        super().log_addition(request, object, message)
        self._create_audit_log(request, object, 'CREATE', message)
    
    def log_change(self, request, object, message):
        """Log object change"""
        super().log_change(request, object, message)
        self._create_audit_log(request, object, 'UPDATE', message)
    
    def log_deletion(self, request, object, object_repr):
        """Log object deletion"""
        super().log_deletion(request, object, object_repr)
        self._create_audit_log(request, object, 'DELETE', f'Deleted {object_repr}')
    
    def _create_audit_log(self, request, object, action, message):
        """Create audit log entry"""
        try:
            from .models import AdminAuditLog
            AdminAuditLog.objects.create(
                user=request.user,
                action=action,
                model_name=object.__class__.__name__,
                object_id=str(object.pk) if hasattr(object, 'pk') else None,
                object_repr=str(object),
                message=message,
                ip_address=self._get_client_ip(request)
            )
        except Exception:
            # Don't fail if audit logging fails
            pass
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class EnhancedModelAdmin(BaseModelAdmin, AdminPermissionMixin, AuditLogMixin):
    """Enhanced model admin with all mixins"""
    pass


@admin.register(Store)
class StoreAdmin(EnhancedModelAdmin):
    """Admin interface for stores"""
    
    list_display = [
        'lid', 'name', 'address', 'phone', 'status', 
        'start_time', 'end_time', 'create_time'
    ]
    list_filter = ['status', 'create_time']
    search_fields = ['lid', 'name', 'address', 'phone']
    ordering = ['-create_time']
    readonly_fields = ['create_time', 'update_time']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('lid', 'name', 'status')
        }),
        ('Location', {
            'fields': ('address', 'detail', 'location')
        }),
        ('Contact', {
            'fields': ('phone',)
        }),
        ('Business Hours', {
            'fields': ('start_time', 'end_time')
        }),
        ('Media', {
            'fields': ('img',)
        }),
        ('Timestamps', {
            'fields': ('create_time', 'update_time'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make lid readonly after creation"""
        readonly = list(super().get_readonly_fields(request, obj))
        if obj:  # Editing existing object
            readonly.append('lid')
        return readonly