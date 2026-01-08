"""
Product service for product creation and update operations.
"""
from uuid import uuid4
from ..models import Product, ProductImage, ProductTag


class ProductService:
    """Service for product creation and update operations"""
    
    @staticmethod
    def create_product(validated_data):
        """
        Create a new product with images and tags.
        
        Args:
            validated_data: Validated data from serializer
            
        Returns:
            Product: Created product instance
        """
        # Extract images and tags data
        images_data = validated_data.pop('images', [])
        tags_data = validated_data.pop('tags', [])
        
        # Auto-generate gid if not provided
        if not validated_data.get('gid'):
            validated_data['gid'] = f"goods_{uuid4().hex[:8]}"
        
        # Create product
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
    
    @staticmethod
    def update_product(instance, validated_data):
        """
        Update an existing product with images and tags.
        
        Args:
            instance: Product instance to update
            validated_data: Validated data from serializer
            
        Returns:
            Product: Updated product instance
        """
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

