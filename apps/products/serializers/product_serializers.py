"""
Product serializers for list, detail, create, and update operations.
"""
from decimal import Decimal
from rest_framework import serializers
from ..models import Product, ProductImage, ProductTag, Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'parent', 'created_at']


class ProductImageSerializer(serializers.ModelSerializer):
    imageUrl = serializers.SerializerMethodField()
    isPrimary = serializers.BooleanField(source='is_primary', read_only=True)
    
    class Meta:
        model = ProductImage
        fields = ['id', 'imageUrl', 'isPrimary', 'order']
    
    def get_imageUrl(self, obj):
        """Return full URL for image"""
        request = self.context.get('request')
        
        # If already a full URL, return as-is
        if obj.image_url.startswith('http://') or obj.image_url.startswith('https://'):
            return obj.image_url
        
        # Build absolute URL from relative path
        if request:
            return request.build_absolute_uri(obj.image_url)
        
        # Fallback to settings
        from django.conf import settings
        backend_url = getattr(settings, 'BACKEND_URL', 'http://localhost:8000').rstrip('/')
        image_path = obj.image_url if obj.image_url.startswith('/') else f'/{obj.image_url}'
        return f"{backend_url}{image_path}"


class ProductTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductTag
        fields = ['id', 'tag']


class ProductListSerializer(serializers.ModelSerializer):
    """Serializer for product list view - GET /api/products/"""
    images = ProductImageSerializer(many=True, read_only=True)
    tags = serializers.SerializerMethodField()
    originalPrice = serializers.SerializerMethodField()
    discountPrice = serializers.SerializerMethodField()
    sold = serializers.SerializerMethodField()
    views = serializers.SerializerMethodField()
    createTime = serializers.DateTimeField(source='create_time', format='%Y-%m-%d %H:%M:%S', read_only=True)
    updateTime = serializers.DateTimeField(source='update_time', format='%Y-%m-%d %H:%M:%S', read_only=True)
    hasTop = serializers.IntegerField(source='has_top', read_only=True)
    hasRecommend = serializers.IntegerField(source='has_recommend', read_only=True)
    isMemberExclusive = serializers.BooleanField(source='is_member_exclusive', read_only=True)
    minTierRequired = serializers.CharField(source='min_tier_required', read_only=True)
    disPrice = serializers.DecimalField(source='dis_price', max_digits=10, decimal_places=2, read_only=True, allow_null=True)
    specification = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'price', 'disPrice', 'originalPrice', 'discountPrice', 'specification', 'description', 
            'status', 'inventory', 'hasTop', 'hasRecommend', 
            'sold', 'views', 'createTime', 'updateTime',
            'images', 'tags', 'isMemberExclusive', 'minTierRequired'
        ]
    
    def get_tags(self, obj):
        """Convert ProductTag objects to simple tag list like Node.js"""
        return [tag.tag for tag in obj.product_tags.all()]
    
    def get_originalPrice(self, obj):
        """Get original price from database (price field)"""
        return float(obj.price)
    
    def get_discountPrice(self, obj):
        """Get discount price from database (dis_price field), fallback to price if not set"""
        if obj.dis_price is not None:
            return float(obj.dis_price)
        return float(obj.price)
    
    def get_disPrice(self, obj):
        """Get original price (dis_price field) - 原价（划痕价）"""
        if obj.dis_price is not None:
            return float(obj.dis_price)
        return None
    
    def get_sold(self, obj):
        """Return sold count from database"""
        return obj.sold
    
    def get_views(self, obj):
        """Return views count from database"""
        return obj.views
    
    def get_sold(self, obj):
        """Return sold count from database"""
        return obj.sold
    
    def get_views(self, obj):
        """Return views count from database"""
        return obj.views


class ProductDetailSerializer(serializers.ModelSerializer):
    """Serializer for product detail view - GET /api/products/{id}/"""
    images = ProductImageSerializer(many=True, read_only=True)
    tags = serializers.SerializerMethodField()
    categoryInfo = CategorySerializer(source='category', read_only=True)
    originalPrice = serializers.SerializerMethodField()
    discountPrice = serializers.SerializerMethodField()
    sold = serializers.SerializerMethodField()
    views = serializers.SerializerMethodField()
    createTime = serializers.DateTimeField(source='create_time', format='%Y-%m-%d %H:%M:%S', read_only=True)
    updateTime = serializers.DateTimeField(source='update_time', format='%Y-%m-%d %H:%M:%S', read_only=True)
    hasTop = serializers.IntegerField(source='has_top', read_only=True)
    hasRecommend = serializers.IntegerField(source='has_recommend', read_only=True)
    isMemberExclusive = serializers.BooleanField(source='is_member_exclusive', read_only=True)
    minTierRequired = serializers.CharField(source='min_tier_required', read_only=True)
    disPrice = serializers.DecimalField(source='dis_price', max_digits=10, decimal_places=2, read_only=True, allow_null=True)
    specification = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'price', 'disPrice', 'originalPrice', 'discountPrice', 'specification', 'description', 'content',
            'status', 'inventory', 'hasTop', 'hasRecommend', 
            'sold', 'views', 'createTime', 'updateTime',
            'images', 'tags', 'categoryInfo', 'isMemberExclusive', 'minTierRequired'
        ]
    
    def get_tags(self, obj):
        """Convert ProductTag objects to simple tag list like Node.js"""
        return [tag.tag for tag in obj.product_tags.all()]
    
    def get_originalPrice(self, obj):
        """Get original price from database (price field)"""
        return float(obj.price)
    
    def get_discountPrice(self, obj):
        """Get discount price from database (dis_price field), fallback to price if not set"""
        if obj.dis_price is not None:
            return float(obj.dis_price)
        return float(obj.price)
    
    def get_disPrice(self, obj):
        """Get original price (dis_price field) - 原价（划痕价）"""
        if obj.dis_price is not None:
            return float(obj.dis_price)
        return None
    
    def get_sold(self, obj):
        """Return sold count from database"""
        return obj.sold
    
    def get_views(self, obj):
        """Return views count from database"""
        return obj.views
    
    def get_sold(self, obj):
        """Return sold count from database"""
        return obj.sold
    
    def get_views(self, obj):
        """Return views count from database"""
        return obj.views


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/updating products - matches Node.js create/updateGoods.
    Used for: POST /api/products/, PUT/PATCH /api/products/{id}/
    Note: Business logic for creating images and tags is handled in ProductService.
    """
    images = serializers.ListField(
        child=serializers.URLField(), 
        write_only=True, 
        required=False,
        help_text="List of image URLs"
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50), 
        write_only=True, 
        required=False,
        help_text="List of tags"
    )
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'price', 'dis_price', 'specification', 'description', 'content',
            'status', 'inventory', 'has_top', 'has_recommend', 
            'category', 'images', 'tags', 'is_member_exclusive', 'min_tier_required'
        ]
    
    def create(self, validated_data):
        """Create product using ProductService"""
        from ..services import ProductService
        return ProductService.create_product(validated_data)
    
    def update(self, instance, validated_data):
        """Update product using ProductService"""
        from ..services import ProductService
        return ProductService.update_product(instance, validated_data)


class AdminProductListSerializer(serializers.ModelSerializer):
    """Serializer for admin product list - matches Node.js adminGetGoodslist response"""
    images = ProductImageSerializer(many=True, read_only=True)
    tags = serializers.SerializerMethodField()
    originalPrice = serializers.SerializerMethodField()
    discountPrice = serializers.SerializerMethodField()
    sold = serializers.SerializerMethodField()
    views = serializers.SerializerMethodField()
    createTime = serializers.DateTimeField(source='create_time', format='%Y-%m-%d %H:%M:%S', read_only=True)
    updateTime = serializers.DateTimeField(source='update_time', format='%Y-%m-%d %H:%M:%S', read_only=True)
    hasTop = serializers.IntegerField(source='has_top', read_only=True)
    hasRecommend = serializers.IntegerField(source='has_recommend', read_only=True)
    isMemberExclusive = serializers.BooleanField(source='is_member_exclusive', read_only=True)
    minTierRequired = serializers.CharField(source='min_tier_required', read_only=True)
    disPrice = serializers.SerializerMethodField()  # 原价（划痕价）
    specification = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'price', 'disPrice', 'originalPrice', 'discountPrice', 'specification', 'description', 'content',
            'status', 'inventory', 'hasTop', 'hasRecommend', 
            'sold', 'views', 'createTime', 'updateTime',
            'images', 'tags', 'isMemberExclusive', 'minTierRequired'
        ]
    
    def get_tags(self, obj):
        """Convert ProductTag objects to simple tag list like Node.js"""
        return [tag.tag for tag in obj.product_tags.all()]
    
    def get_originalPrice(self, obj):
        """Get original price from database (price field)"""
        return float(obj.price)
    
    def get_discountPrice(self, obj):
        """Get discount price from database (dis_price field), fallback to price if not set"""
        if obj.dis_price is not None:
            return float(obj.dis_price)
        return float(obj.price)
    
    def get_disPrice(self, obj):
        """Get original price (dis_price field) - 原价（划痕价）"""
        if obj.dis_price is not None:
            return float(obj.dis_price)
        return None
    
    def get_sold(self, obj):
        """Return sold count from database"""
        return obj.sold
    
    def get_views(self, obj):
        """Return views count from database"""
        return obj.views

