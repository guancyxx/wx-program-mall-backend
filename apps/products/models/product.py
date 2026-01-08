from django.db import models


class Product(models.Model):
    """Product model - uses Django primary key (id) instead of gid"""
    # Core fields
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    dis_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Discount price (disPrice in Node.js)")
    specification = models.DecimalField(max_digits=10, decimal_places=2, default=1.0, help_text="Product specification in kilograms (规格，单位：公斤)")
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
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True)
    
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
            models.Index(fields=['status']),
            models.Index(fields=['has_top', 'has_recommend']),
            models.Index(fields=['create_time']),
        ]

    def __str__(self):
        return f"{self.name} (id: {self.id})"

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


