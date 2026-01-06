from rest_framework import serializers
from .models import Category, Product, ProductImage, ProductTag, Banner


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
    """Serializer for product list view - matches Node.js getGoodsList response"""
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
    """Serializer for product detail view - matches Node.js getGoodsDetail response"""
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
    """Serializer for creating/updating products - matches Node.js create/updateGoods"""
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
        from uuid import uuid4
        
        images_data = validated_data.pop('images', [])
        tags_data = validated_data.pop('tags', [])
        
        # Auto-generate gid if not provided
        if not validated_data.get('gid'):
            validated_data['gid'] = f"goods_{uuid4().hex[:8]}"
        
        product = Product.objects.create(**validated_data)
        
        # Create images
        for i, image_url in enumerate(images_data):
            ProductImage.objects.create(
                product=product,
                image_url=image_url,
                is_primary=(i == 0),  # First image is primary
                order=i
            )
        
        # Create tags
        for tag in tags_data:
            ProductTag.objects.create(product=product, tag=tag)
        
        return product
    
    def update(self, instance, validated_data):
        images_data = validated_data.pop('images', None)
        tags_data = validated_data.pop('tags', None)
        
        # Update product fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update images if provided
        if images_data is not None:
            instance.images.all().delete()
            for i, image_url in enumerate(images_data):
                ProductImage.objects.create(
                    product=instance,
                    image_url=image_url,
                    is_primary=(i == 0),
                    order=i
                )
        
        # Update tags if provided
        if tags_data is not None:
            instance.product_tags.all().delete()
            for tag in tags_data:
                ProductTag.objects.create(product=instance, tag=tag)
        
        return instance


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


class BannerSerializer(serializers.ModelSerializer):
    """Serializer for banner data - matches frontend expected format"""
    
    class Meta:
        model = Banner
        fields = ['id', 'cover', 'title', 'type']