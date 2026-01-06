from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Category(models.Model):
    """Product categories for future use"""
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_categories'
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Product(models.Model):
    """Product model matching Node.js goods schema exactly"""
    # Core fields matching Node.js schema
    gid = models.CharField(max_length=100, unique=True, help_text="Product ID from Node.js")
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    dis_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Discount price (disPrice in Node.js)")
    description = models.TextField(blank=True, default='')
    content = models.TextField(blank=True, default='', help_text="Detailed product content")
    
    # Status and flags matching Node.js
    status = models.IntegerField(default=1, help_text="1=active, -1=inactive")
    has_top = models.IntegerField(default=0, help_text="0=normal, 1=pinned (hasTop in Node.js)")
    has_recommend = models.IntegerField(default=0, help_text="0=normal, 1=recommended (hasRecommend in Node.js)")
    
    # Inventory and sales tracking
    inventory = models.IntegerField(default=0, help_text="Stock quantity")
    sold = models.IntegerField(default=0, help_text="Sold quantity")
    views = models.IntegerField(default=0, help_text="View count")
    
    # Timestamps matching Node.js
    create_time = models.DateTimeField(auto_now_add=True, help_text="createTime in Node.js")
    update_time = models.DateTimeField(auto_now=True, help_text="updateTime in Node.js")
    
    # Future category support
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Member-exclusive features (new functionality)
    is_member_exclusive = models.BooleanField(default=False)
    min_tier_required = models.CharField(
        max_length=20, 
        choices=[('Bronze', 'Bronze'), ('Silver', 'Silver'), ('Gold', 'Gold'), ('Platinum', 'Platinum')],
        null=True, 
        blank=True
    )

    class Meta:
        db_table = 'products'
        indexes = [
            models.Index(fields=['gid']),
            models.Index(fields=['status']),
            models.Index(fields=['has_top', 'has_recommend']),
            models.Index(fields=['create_time']),
        ]

    def __str__(self):
        return f"{self.name} (gid: {self.gid})"

    @property
    def is_active(self):
        """Compatibility property for Django conventions"""
        return self.status == 1

    @property
    def is_featured(self):
        """Compatibility property for Django conventions"""
        return self.has_recommend == 1

    @property
    def is_pinned(self):
        """Check if product is pinned/top"""
        return self.has_top == 1


class ProductImage(models.Model):
    """Product images - replaces images array from Node.js"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image_url = models.URLField(max_length=500)
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0, help_text="Display order")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_images'
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['product', 'is_primary']),
            models.Index(fields=['product', 'order']),
        ]

    def __str__(self):
        return f"Image for {self.product.name}"


class ProductTag(models.Model):
    """Product tags - replaces tags array from Node.js"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_tags')
    tag = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_tags'
        unique_together = ['product', 'tag']
        indexes = [
            models.Index(fields=['tag']),
            models.Index(fields=['product']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.tag}"


class Banner(models.Model):
    """Home page banner/carousel model"""
    TYPE_CHOICES = [
        (1, '小程序内部'),
        (2, '外部小程序'),
        (3, '外部网站'),
    ]
    
    cover = models.CharField(max_length=500, help_text="Banner image URL")
    title = models.CharField(max_length=200, help_text="Jump link/title")
    type = models.IntegerField(choices=TYPE_CHOICES, default=1, help_text="Jump type: 1=internal, 2=external mini-program, 3=external website")
    order = models.IntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True, help_text="Whether banner is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'banners'
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['is_active', 'order']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Banner {self.id}: {self.title}"