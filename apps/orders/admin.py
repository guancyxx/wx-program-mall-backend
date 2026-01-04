from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from .models import Order, OrderItem, ReturnOrder, OrderDiscount


class OrderItemInline(admin.TabularInline):
    """Inline admin for order items"""
    model = OrderItem
    extra = 0
    readonly_fields = ['rrid', 'amount', 'created_at']
    fields = ['rrid', 'gid', 'quantity', 'price', 'amount', 'is_return', 'product_info']


class OrderDiscountInline(admin.TabularInline):
    """Inline admin for order discounts"""
    model = OrderDiscount
    extra = 0
    readonly_fields = ['created_at']
    fields = ['discount_type', 'discount_amount', 'description', 'discount_details']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Enhanced admin interface for orders"""
    
    list_display = [
        'roid', 'user_link', 'status_display', 'amount', 'type', 
        'create_time', 'pay_time', 'order_age', 'verify_status'
    ]
    list_filter = [
        'status', 'type', 'verify_status', 'create_time', 'pay_time'
    ]
    search_fields = ['roid', 'uid__username', 'uid__phone', 'openid']
    ordering = ['-create_time']
    readonly_fields = [
        'roid', 'create_time', 'pay_time', 'send_time', 'verify_time',
        'order_age', 'order_summary', 'payment_info'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('roid', 'uid', 'lid', 'openid', 'order_summary')
        }),
        ('Order Details', {
            'fields': ('amount', 'status', 'type', 'remark', 'address')
        }),
        ('Timestamps & Age', {
            'fields': ('create_time', 'pay_time', 'send_time', 'lock_timeout', 'order_age')
        }),
        ('Payment Information', {
            'fields': ('payment_info',),
            'classes': ('collapse',)
        }),
        ('Logistics & Delivery', {
            'fields': ('logistics',),
            'classes': ('collapse',)
        }),
        ('Refund Information', {
            'fields': ('refund_info', 'cancel_text'),
            'classes': ('collapse',)
        }),
        ('Verification (Pickup Orders)', {
            'fields': ('qrcode', 'verify_time', 'verify_status'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [OrderItemInline, OrderDiscountInline]
    
    def user_link(self, obj):
        """Link to user admin page"""
        if obj.uid:
            url = reverse('admin:users_user_change', args=[obj.uid.id])
            return format_html('<a href="{}">{}</a>', url, obj.uid.username)
        return 'No user'
    user_link.short_description = 'User'
    user_link.admin_order_field = 'uid__username'
    
    def status_display(self, obj):
        """Display order status with color coding"""
        status_colors = {
            -1: '#dc3545',  # Cancelled - Red
            0: '#ffc107',   # Pending Payment - Yellow
            1: '#28a745',   # Paid - Green
            2: '#17a2b8',   # Processing - Blue
            3: '#6f42c1',   # Shipped - Purple
            4: '#20c997',   # Delivered - Teal
            5: '#fd7e14',   # Refunding - Orange
            6: '#6c757d',   # Refunded - Gray
            7: '#e83e8c',   # Returned - Pink
        }
        
        status_names = {
            -1: 'Cancelled',
            0: 'Pending Payment',
            1: 'Paid',
            2: 'Processing',
            3: 'Shipped',
            4: 'Delivered',
            5: 'Refunding',
            6: 'Refunded',
            7: 'Returned',
        }
        
        color = status_colors.get(obj.status, '#000000')
        name = status_names.get(obj.status, f'Status {obj.status}')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, name
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def order_age(self, obj):
        """Calculate and display order age"""
        from django.utils import timezone
        age = timezone.now() - obj.create_time
        
        if age.days > 0:
            return f"{age.days} days ago"
        elif age.seconds > 3600:
            hours = age.seconds // 3600
            return f"{hours} hours ago"
        else:
            minutes = age.seconds // 60
            return f"{minutes} minutes ago"
    order_age.short_description = 'Order Age'
    
    def order_summary(self, obj):
        """Display order summary with items"""
        items = obj.items.all()
        if not items:
            return 'No items'
        
        html = '<div>'
        for item in items[:3]:  # Show first 3 items
            html += f'<div>• {item.gid} (Qty: {item.quantity}) - ${item.amount}</div>'
        
        if items.count() > 3:
            html += f'<div><em>... and {items.count() - 3} more items</em></div>'
        
        html += f'<div><strong>Total: ${obj.amount}</strong></div>'
        html += '</div>'
        
        return mark_safe(html)
    order_summary.short_description = 'Order Summary'
    
    def payment_info(self, obj):
        """Display payment information"""
        try:
            payment = obj.payment_transactions.first()
            if payment:
                html = f"""
                <div>
                    <strong>Payment Method:</strong> {payment.payment_method}<br>
                    <strong>Transaction ID:</strong> {payment.transaction_id}<br>
                    <strong>Status:</strong> {payment.get_status_display()}<br>
                    <strong>Amount:</strong> ${payment.amount}
                </div>
                """
                return mark_safe(html)
        except:
            pass
        return 'No payment information'
    payment_info.short_description = 'Payment Details'
    
    def get_queryset(self, request):
        """Optimize queryset with related objects"""
        return super().get_queryset(request).select_related('uid').prefetch_related(
            'items', 'discounts', 'payment_transactions'
        )
    
    actions = ['mark_as_shipped', 'mark_as_delivered', 'cancel_orders', 'export_orders']
    
    def mark_as_shipped(self, request, queryset):
        """Mark selected orders as shipped"""
        from django.utils import timezone
        updated_count = 0
        for order in queryset.filter(status=1):  # Only paid orders
            order.status = 3  # Shipped
            order.send_time = timezone.now()
            order.save()
            updated_count += 1
        
        self.message_user(request, f'{updated_count} orders marked as shipped.')
    mark_as_shipped.short_description = 'Mark as shipped'
    
    def mark_as_delivered(self, request, queryset):
        """Mark selected orders as delivered"""
        updated_count = 0
        for order in queryset.filter(status=3):  # Only shipped orders
            order.status = 4  # Delivered
            order.save()
            updated_count += 1
        
        self.message_user(request, f'{updated_count} orders marked as delivered.')
    mark_as_delivered.short_description = 'Mark as delivered'
    
    def cancel_orders(self, request, queryset):
        """Cancel selected orders"""
        updated_count = 0
        for order in queryset.filter(status__in=[0, 1]):  # Pending or paid orders
            order.status = -1  # Cancelled
            order.cancel_text = 'Cancelled by admin'
            order.save()
            updated_count += 1
        
        self.message_user(request, f'{updated_count} orders cancelled.')
    cancel_orders.short_description = 'Cancel orders'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Admin interface for order items"""
    
    list_display = ['rrid', 'order', 'gid', 'quantity', 'price', 'amount', 'is_return']
    list_filter = ['is_return', 'created_at']
    search_fields = ['rrid', 'gid', 'order__roid']
    ordering = ['-created_at']
    readonly_fields = ['rrid', 'amount', 'created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('rrid', 'order', 'gid')
        }),
        ('Product Details', {
            'fields': ('quantity', 'price', 'amount', 'product_info')
        }),
        ('Return Status', {
            'fields': ('is_return',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )


@admin.register(ReturnOrder)
class ReturnOrderAdmin(admin.ModelAdmin):
    """Admin interface for return orders"""
    
    list_display = ['rrid', 'roid', 'uid', 'gid', 'amount', 'refund_amount', 'status', 'create_time']
    list_filter = ['status', 'create_time']
    search_fields = ['rrid', 'roid', 'gid', 'uid__username', 'openid']
    ordering = ['-create_time']
    readonly_fields = ['rrid', 'create_time']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('rrid', 'roid', 'uid', 'gid', 'openid')
        }),
        ('Return Details', {
            'fields': ('amount', 'refund_amount', 'status')
        }),
        ('Timestamps', {
            'fields': ('create_time',)
        }),
    )


@admin.register(OrderDiscount)
class OrderDiscountAdmin(admin.ModelAdmin):
    """Admin interface for order discounts"""
    
    list_display = ['order', 'discount_type', 'discount_amount', 'description', 'created_at']
    list_filter = ['discount_type', 'created_at']
    search_fields = ['order__roid', 'description']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('order', 'discount_type')
        }),
        ('Discount Details', {
            'fields': ('discount_amount', 'description', 'discount_details')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )