from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Category, Product, ProductImage, ProductTag, Banner


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image_url', 'is_primary', 'order']


class ProductTagInline(admin.TabularInline):
    model = ProductTag
    extra = 1
    fields = ['tag']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'created_at']
    list_filter = ['parent', 'created_at']
    search_fields = ['name']
    ordering = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'gid', 'name', 'price', 'dis_price', 'status', 
        'inventory_status', 'sold', 'views', 'has_top', 'has_recommend'
    ]
    list_filter = [
        'status', 'has_top', 'has_recommend', 'is_member_exclusive', 
        'min_tier_required', 'category', 'create_time'
    ]
    search_fields = ['gid', 'name', 'description']
    readonly_fields = ['create_time', 'update_time', 'views', 'sold']
    ordering = ['-create_time']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('gid', 'name', 'description', 'content', 'category')
        }),
        ('Pricing', {
            'fields': ('price', 'dis_price')
        }),
        ('Status & Features', {
            'fields': ('status', 'has_top', 'has_recommend')
        }),
        ('Inventory & Sales', {
            'fields': ('inventory', 'sold', 'views', 'inventory_alerts')
        }),
        ('Member Features', {
            'fields': ('is_member_exclusive', 'min_tier_required')
        }),
        ('Timestamps', {
            'fields': ('create_time', 'update_time'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ProductImageInline, ProductTagInline]
    
    def inventory_status(self, obj):
        """Display inventory status with color coding"""
        if obj.inventory <= 0:
            return format_html(
                '<span style="color: red; font-weight: bold;">Out of Stock</span>'
            )
        elif obj.inventory <= 10:
            return format_html(
                '<span style="color: orange; font-weight: bold;">{} (Low Stock)</span>',
                obj.inventory
            )
        else:
            return format_html(
                '<span style="color: green;">{}</span>',
                obj.inventory
            )
    inventory_status.short_description = 'Inventory'
    inventory_status.admin_order_field = 'inventory'
    
    def inventory_alerts(self, obj):
        """Display inventory alerts and recommendations"""
        alerts = []
        
        if obj.inventory <= 0:
            alerts.append('⚠️ Product is out of stock')
        elif obj.inventory <= 10:
            alerts.append(f'⚠️ Low stock warning: Only {obj.inventory} items left')
        
        if obj.sold > 100 and obj.inventory <= 20:
            alerts.append('📈 Popular item with low stock - consider restocking')
        
        if not alerts:
            alerts.append('✅ Inventory levels are healthy')
        
        return mark_safe('<br>'.join(alerts))
    inventory_alerts.short_description = 'Inventory Alerts'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')
    
    actions = ['mark_as_featured', 'unmark_as_featured', 'restock_products', 'mark_out_of_stock']
    
    def mark_as_featured(self, request, queryset):
        """Mark selected products as featured"""
        updated = queryset.update(has_recommend=True)
        self.message_user(request, f'{updated} products marked as featured.')
    mark_as_featured.short_description = 'Mark as featured'
    
    def unmark_as_featured(self, request, queryset):
        """Unmark selected products as featured"""
        updated = queryset.update(has_recommend=False)
        self.message_user(request, f'{updated} products unmarked as featured.')
    unmark_as_featured.short_description = 'Unmark as featured'
    
    def restock_products(self, request, queryset):
        """Quick restock action - adds 50 to inventory"""
        updated_count = 0
        for product in queryset:
            product.inventory += 50
            product.save()
            updated_count += 1
        
        self.message_user(request, f'{updated_count} products restocked (+50 each).')
    restock_products.short_description = 'Quick restock (+50 inventory)'
    
    def mark_out_of_stock(self, request, queryset):
        """Mark selected products as out of stock"""
        updated = queryset.update(inventory=0, status=0)
        self.message_user(request, f'{updated} products marked as out of stock.')
    mark_out_of_stock.short_description = 'Mark as out of stock'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'image_url', 'is_primary', 'order', 'created_at']
    list_filter = ['is_primary', 'created_at']
    search_fields = ['product__name', 'product__gid']
    ordering = ['product', 'order']


@admin.register(ProductTag)
class ProductTagAdmin(admin.ModelAdmin):
    list_display = ['product', 'tag', 'created_at']
    list_filter = ['tag', 'created_at']
    search_fields = ['product__name', 'product__gid', 'tag']
    ordering = ['tag']


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'type', 'order', 'is_active', 'created_at']
    list_filter = ['type', 'is_active', 'created_at']
    search_fields = ['title', 'cover']
    ordering = ['order', 'created_at']
    list_editable = ['order', 'is_active']
    
    fieldsets = (
        ('Banner Information', {
            'fields': ('cover', 'title', 'type')
        }),
        ('Display Settings', {
            'fields': ('order', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request)