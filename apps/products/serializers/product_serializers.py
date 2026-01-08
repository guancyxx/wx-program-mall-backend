"""
Product serializers for list, detail, create, and update operations.
"""
from rest_framework import serializers
from ..models import Product, ProductImage, ProductTag, Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'parent', 'created_at']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image_url', 'is_primary', 'order']


class ProductTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductTag
        fields = ['id', 'tag']


class ProductListSerializer(serializers.ModelSerializer):
    """Serializer for product list view - GET /api/products/"""
    images = ProductImageSerializer(many=True, read_only=True)
    tags = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'gid', 'name', 'price', 'dis_price', 'description', 
            'status', 'inventory', 'has_top', 'has_recommend', 
            'sold', 'views', 'create_time', 'update_time',
            'images', 'tags', 'is_member_exclusive', 'min_tier_required'
        ]
    
    def get_tags(self, obj):
        """Convert ProductTag objects to simple tag list like Node.js"""
        return [tag.tag for tag in obj.product_tags.all()]


class ProductDetailSerializer(serializers.ModelSerializer):
    """Serializer for product detail view - GET /api/products/{gid}/"""
    images = ProductImageSerializer(many=True, read_only=True)
    tags = serializers.SerializerMethodField()
    category_info = CategorySerializer(source='category', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'gid', 'name', 'price', 'dis_price', 'description', 'content',
            'status', 'inventory', 'has_top', 'has_recommend', 
            'sold', 'views', 'create_time', 'update_time',
            'images', 'tags', 'category_info', 'is_member_exclusive', 'min_tier_required'
        ]
    
    def get_tags(self, obj):
        """Convert ProductTag objects to simple tag list like Node.js"""
        return [tag.tag for tag in obj.product_tags.all()]


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
    gid = serializers.CharField(required=False, help_text="Product ID - auto-generated if not provided")
    
    class Meta:
        model = Product
        fields = [
            'gid', 'name', 'price', 'dis_price', 'description', 'content',
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
    
    class Meta:
        model = Product
        fields = [
            'gid', 'name', 'price', 'dis_price', 'description', 
            'status', 'inventory', 'has_top', 'has_recommend', 
            'sold', 'views', 'create_time', 'update_time',
            'images', 'tags', 'is_member_exclusive', 'min_tier_required'
        ]
    
    def get_tags(self, obj):
        """Convert ProductTag objects to simple tag list like Node.js"""
        return [tag.tag for tag in obj.product_tags.all()]

