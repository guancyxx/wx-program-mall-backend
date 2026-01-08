"""
Product services for member-exclusive features and product management
"""
from django.db.models import Q
from apps.membership.models import MembershipStatus, MembershipTier
from .models import Product, ProductImage, ProductTag


class ProductMemberService:
    """Service for handling member-exclusive product features"""
    
    TIER_HIERARCHY = {
        'Bronze': 1,
        'Silver': 2,
        'Gold': 3,
        'Platinum': 4
    }
    
    @classmethod
    def get_user_tier_level(cls, user):
        """Get user's membership tier level"""
        if not user or not user.is_authenticated:
            return 0  # Non-member
        
        try:
            membership = MembershipStatus.objects.select_related('tier').get(user=user)
            return cls.TIER_HIERARCHY.get(membership.tier.name, 0)
        except MembershipStatus.DoesNotExist:
            return 1  # Default Bronze level
    
    @classmethod
    def filter_accessible_products(cls, queryset, user):
        """Filter products based on user's membership tier"""
        user_tier_level = cls.get_user_tier_level(user)
        
        # Build filter for accessible products
        accessible_filter = Q(is_member_exclusive=False)  # Non-exclusive products
        
        if user_tier_level > 0:
            # Add member-exclusive products that user can access
            for tier_name, tier_level in cls.TIER_HIERARCHY.items():
                if user_tier_level >= tier_level:
                    accessible_filter |= Q(
                        is_member_exclusive=True,
                        min_tier_required=tier_name
                    )
        
        return queryset.filter(accessible_filter)
    
    @classmethod
    def get_member_discount(cls, product, user):
        """Calculate member-specific discount for a product"""
        if not user or not user.is_authenticated:
            return 0
        
        try:
            membership = MembershipStatus.objects.select_related('tier').get(user=user)
            tier_name = membership.tier.name
            
            # Define tier-based discounts
            tier_discounts = {
                'Bronze': 0.0,    # No additional discount
                'Silver': 0.05,   # 5% discount
                'Gold': 0.10,     # 10% discount
                'Platinum': 0.15  # 15% discount
            }
            
            return tier_discounts.get(tier_name, 0.0)
        except MembershipStatus.DoesNotExist:
            return 0.0
    
    @classmethod
    def get_member_price(cls, product, user):
        """Get the final price for a member including tier discounts"""
        base_price = product.dis_price if product.dis_price else product.price
        discount_rate = cls.get_member_discount(product, user)
        
        if discount_rate > 0:
            member_price = float(base_price) * (1 - discount_rate)
            return round(member_price, 2)
        
        return float(base_price)
    
    @classmethod
    def has_early_access(cls, user):
        """Check if user has early access to new products (Gold/Platinum only)"""
        user_tier_level = cls.get_user_tier_level(user)
        return user_tier_level >= cls.TIER_HIERARCHY['Gold']
    
    @classmethod
    def can_access_product(cls, product, user):
        """Check if user can access a specific product"""
        if not product.is_member_exclusive:
            return True
        
        if not user or not user.is_authenticated:
            return False
        
        user_tier_level = cls.get_user_tier_level(user)
        required_tier_level = cls.TIER_HIERARCHY.get(product.min_tier_required, 0)
        
        return user_tier_level >= required_tier_level
    
    @classmethod
    def get_product_with_member_info(cls, product, user):
        """Get product data enriched with member-specific information"""
        product_data = {
            'gid': product.gid,
            'name': product.name,
            'price': float(product.price),
            'dis_price': float(product.dis_price) if product.dis_price else None,
            'description': product.description,
            'content': product.content,
            'status': product.status,
            'inventory': product.inventory,
            'has_top': product.has_top,
            'has_recommend': product.has_recommend,
            'sold': product.sold,
            'views': product.views,
            'create_time': product.create_time,
            'update_time': product.update_time,
            'is_member_exclusive': product.is_member_exclusive,
            'min_tier_required': product.min_tier_required,
        }
        
        # Add member-specific pricing and access info
        if user and user.is_authenticated:
            product_data.update({
                'member_price': cls.get_member_price(product, user),
                'member_discount_rate': cls.get_member_discount(product, user),
                'can_access': cls.can_access_product(product, user),
                'user_tier_level': cls.get_user_tier_level(user),
            })
        else:
            product_data.update({
                'member_price': float(product.dis_price) if product.dis_price else float(product.price),
                'member_discount_rate': 0.0,
                'can_access': not product.is_member_exclusive,
                'user_tier_level': 0,
            })
        
        return product_data


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
        from uuid import uuid4
        
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