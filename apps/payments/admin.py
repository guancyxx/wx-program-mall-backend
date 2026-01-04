from django.contrib import admin
from django.utils.html import format_html
from .models import PaymentMethod, PaymentTransaction, RefundRequest, WeChatPayment, PaymentCallback


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'is_active', 'sort_order', 'created_at']
    list_filter = ['is_active', 'name']
    search_fields = ['name', 'display_name']
    ordering = ['sort_order', 'name']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'display_name', 'is_active', 'sort_order')
        }),
        ('Configuration', {
            'fields': ('config',),
            'classes': ('collapse',)
        }),
    )


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_id', 'order_id', 'user', 'payment_method', 
        'amount', 'status', 'created_at', 'paid_at'
    ]
    list_filter = ['status', 'payment_method', 'created_at', 'paid_at']
    search_fields = ['transaction_id', 'order_id', 'external_transaction_id', 'user__username']
    readonly_fields = ['transaction_id', 'created_at', 'updated_at', 'paid_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('transaction_id', 'order_id', 'user', 'payment_method')
        }),
        ('Payment Details', {
            'fields': ('amount', 'currency', 'status', 'created_at', 'paid_at', 'expired_at')
        }),
        ('External System', {
            'fields': ('external_transaction_id', 'external_order_id'),
            'classes': ('collapse',)
        }),
        ('WeChat Pay', {
            'fields': ('wechat_openid', 'wechat_prepay_id'),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('payment_data', 'callback_data', 'callback_received_at'),
            'classes': ('collapse',)
        }),
        ('Error Information', {
            'fields': ('error_code', 'error_message'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            return self.readonly_fields + ['user', 'payment_method', 'amount', 'order_id']
        return self.readonly_fields


@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    list_display = [
        'refund_id', 'order_id', 'refund_type', 'refund_amount', 
        'status', 'requested_at', 'completed_at'
    ]
    list_filter = ['status', 'refund_type', 'requested_at', 'completed_at']
    search_fields = ['refund_id', 'order_id', 'return_order_id', 'external_refund_id']
    readonly_fields = ['refund_id', 'requested_at', 'processed_at', 'completed_at', 'updated_at']
    ordering = ['-requested_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('refund_id', 'original_transaction', 'order_id', 'return_order_id')
        }),
        ('Refund Details', {
            'fields': ('refund_type', 'refund_amount', 'refund_reason', 'status')
        }),
        ('Timestamps', {
            'fields': ('requested_at', 'processed_at', 'completed_at'),
            'classes': ('collapse',)
        }),
        ('External System', {
            'fields': ('external_refund_id',),
            'classes': ('collapse',)
        }),
        ('Processing', {
            'fields': ('processed_by', 'admin_notes'),
            'classes': ('collapse',)
        }),
        ('Error Information', {
            'fields': ('error_code', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('refund_data',),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            return self.readonly_fields + ['original_transaction', 'refund_amount', 'refund_type']
        return self.readonly_fields


@admin.register(WeChatPayment)
class WeChatPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'out_trade_no', 'payment_transaction', 'total_fee', 
        'prepay_id', 'transaction_id', 'created_at'
    ]
    list_filter = ['created_at', 'bank_type']
    search_fields = ['out_trade_no', 'prepay_id', 'transaction_id', 'payment_transaction__transaction_id']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('payment_transaction', 'appid', 'mch_id', 'out_trade_no')
        }),
        ('Order Details', {
            'fields': ('body', 'total_fee', 'spbill_create_ip', 'nonce_str')
        }),
        ('WeChat Response', {
            'fields': ('prepay_id', 'code_url', 'transaction_id', 'bank_type'),
            'classes': ('collapse',)
        }),
        ('Settlement', {
            'fields': ('settlement_total_fee', 'cash_fee'),
            'classes': ('collapse',)
        }),
        ('Signature', {
            'fields': ('sign', 'sign_type'),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('wechat_data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PaymentCallback)
class PaymentCallbackAdmin(admin.ModelAdmin):
    list_display = [
        'callback_type', 'payment_method', 'transaction_id', 
        'processed', 'response_status', 'received_at'
    ]
    list_filter = ['callback_type', 'payment_method', 'processed', 'response_status', 'received_at']
    search_fields = ['transaction_id', 'refund_id', 'request_path']
    readonly_fields = ['received_at']
    ordering = ['-received_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('callback_type', 'payment_method', 'transaction_id', 'refund_id')
        }),
        ('Request Details', {
            'fields': ('request_method', 'request_path', 'request_ip'),
        }),
        ('Processing', {
            'fields': ('processed', 'processing_error', 'response_status'),
        }),
        ('Request Data', {
            'fields': ('request_headers', 'request_body'),
            'classes': ('collapse',)
        }),
        ('Response Data', {
            'fields': ('response_body',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('received_at',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Callbacks are created automatically, not manually
        return False
    
    def has_change_permission(self, request, obj=None):
        # Callbacks should not be modified after creation
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Allow deletion for cleanup purposes
        return request.user.is_superuser