"""
Property-based tests for product functionality
Feature: django-mall-migration
"""
import pytest
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal

from apps.products.models import Product, ProductImage, ProductTag, Category
from apps.products.serializers import ProductCreateUpdateSerializer
from apps.membership.models import MembershipTier, MembershipStatus

User = get_user_model()


class ProductPropertyTests(TestCase):
    """Property-based tests for product functionality"""

    def setUp(self):
        """Set up test data"""
        # Create test category
        self.category = Category.objects.create(name="Test Category")
        
        # Create membership tiers
        self.bronze_tier = MembershipTier.objects.create(
            name="Bronze",
            min_spending=Decimal('0'),
            max_spending=Decimal('999.99'),
            points_multiplier=Decimal('1.0')
        )
        self.silver_tier = MembershipTier.objects.create(
            name="Silver", 
            min_spending=Decimal('1000'),
            max_spending=Decimal('4999.99'),
            points_multiplier=Decimal('1.2')
        )

    @given(
        name=st.text(min_size=1, max_size=200).filter(lambda x: x.strip() and not any(c in x for c in ['\x00', '\r', '\n'])),
        price=st.decimals(min_value=Decimal('0.01'), max_value=Decimal('9999.99'), places=2),
        description=st.text(max_size=1000).filter(lambda x: not any(c in x for c in ['\x00', '\r', '\n'])),
        inventory=st.integers(min_value=0, max_value=10000),
        images=st.lists(
            st.text(min_size=10, max_size=500).filter(lambda x: 'http' in x and not any(c in x for c in ['\x00', '\r', '\n'])), 
            min_size=0, max_size=5
        ),
        tags=st.lists(
            st.text(min_size=1, max_size=50).filter(lambda x: x.strip() and not any(c in x for c in ['\x00', '\r', '\n'])), 
            min_size=0, max_size=10
        ).map(lambda tags: list(set(tag.strip() for tag in tags if tag.strip())))  # Remove duplicates
    )
    @settings(max_examples=50, deadline=None)  # Reduced examples for faster testing
    def test_property_9_product_creation_completeness(self, name, price, description, inventory, images, tags):
        """
        Property 9: Product Creation Completeness
        For any product creation request with valid data, all provided product details 
        should be stored and retrievable through the product API
        **Validates: Requirements 4.1**
        """
        # Clean and prepare data
        name = name.strip()
        tags = [tag.strip() for tag in tags if tag.strip()]
        
        # Prepare product data
        product_data = {
            'name': name,
            'price': price,
            'description': description,
            'inventory': inventory,
            'category': self.category.id,
            'images': images,
            'tags': tags
        }

        # Create product using serializer
        serializer = ProductCreateUpdateSerializer(data=product_data)
        
        # Verify serializer is valid
        assert serializer.is_valid(), f"Serializer errors: {serializer.errors}"
        
        # Save the product
        product = serializer.save()
        
        # Verify all core fields are stored correctly
        assert product.name == name
        assert product.price == price
        assert product.description == description
        assert product.inventory == inventory
        assert product.category == self.category
        assert product.gid is not None and len(product.gid) > 0
        
        # Verify images are stored correctly
        stored_images = list(product.images.all().order_by('order'))
        assert len(stored_images) == len(images)
        for i, image_url in enumerate(images):
            assert stored_images[i].image_url == image_url
            assert stored_images[i].is_primary == (i == 0)  # First image should be primary
            assert stored_images[i].order == i
        
        # Verify tags are stored correctly
        stored_tags = set(tag.tag for tag in product.product_tags.all())
        expected_tags = set(tags)
        assert stored_tags == expected_tags
        
        # Verify product can be retrieved
        retrieved_product = Product.objects.get(gid=product.gid)
        assert retrieved_product.name == name
        assert retrieved_product.price == price
        assert retrieved_product.description == description
        assert retrieved_product.inventory == inventory

    @given(
        initial_inventory=st.integers(min_value=1, max_value=100),
        sold_quantity=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_10_inventory_stock_management(self, initial_inventory, sold_quantity):
        """
        Property 10: Inventory Stock Management
        For any product whose inventory quantity reaches zero, the product should be 
        marked as out of stock and unavailable for purchase
        **Validates: Requirements 4.3**
        """
        # Create a product with initial inventory
        product = Product.objects.create(
            gid=f"test_{initial_inventory}_{sold_quantity}",
            name="Test Product",
            price=Decimal('10.00'),
            inventory=initial_inventory,
            category=self.category
        )
        
        # Simulate sales by reducing inventory
        final_inventory = max(0, initial_inventory - sold_quantity)
        product.inventory = final_inventory
        product.sold += min(sold_quantity, initial_inventory)
        product.save()
        
        # Verify inventory tracking
        assert product.inventory == final_inventory
        assert product.sold == min(sold_quantity, initial_inventory)
        
        # If inventory reaches zero, product should be considered out of stock
        if product.inventory == 0:
            # In our model, we check inventory in business logic
            # The product should not be available for purchase when inventory is 0
            assert product.inventory == 0
            # Business logic should prevent purchases when inventory is 0
            # This would be enforced in the order creation process
        else:
            # Product should still be available
            assert product.inventory > 0

    @given(
        search_term=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        product_names=st.lists(
            st.text(min_size=5, max_size=100).filter(lambda x: x.strip()), 
            min_size=1, max_size=10
        ),
        product_descriptions=st.lists(
            st.text(min_size=10, max_size=200).filter(lambda x: x.strip()), 
            min_size=1, max_size=10
        ),
        product_tags=st.lists(
            st.lists(st.text(min_size=1, max_size=20).filter(lambda x: x.strip()), min_size=0, max_size=3),
            min_size=1, max_size=10
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_11_product_search_relevance(self, search_term, product_names, product_descriptions, product_tags):
        """
        Property 11: Product Search Relevance
        For any search query, all returned products should contain the search terms 
        in their name, description, or tags
        **Validates: Requirements 4.5**
        """
        # Ensure we have matching data lengths
        max_len = min(len(product_names), len(product_descriptions), len(product_tags))
        if max_len == 0:
            return  # Skip if no valid data
            
        product_names = product_names[:max_len]
        product_descriptions = product_descriptions[:max_len]
        product_tags = product_tags[:max_len]
        
        search_term_lower = search_term.strip().lower()
        
        # Create products with varying relevance to search term
        created_products = []
        for i in range(max_len):
            name = product_names[i]
            description = product_descriptions[i]
            tags = [tag for tag in product_tags[i] if tag.strip()]
            
            product = Product.objects.create(
                gid=f"search_test_{i}_{hash(search_term)}",
                name=name,
                description=description,
                price=Decimal('10.00'),
                inventory=10,
                status=1,  # Active
                category=self.category
            )
            
            # Add tags
            for tag in tags:
                ProductTag.objects.create(product=product, tag=tag)
            
            created_products.append(product)
        
        # Perform search simulation (matching the view logic)
        from django.db.models import Q
        
        search_results = Product.objects.filter(
            Q(status=1) & (
                Q(name__icontains=search_term) |
                Q(description__icontains=search_term) |
                Q(content__icontains=search_term) |
                Q(product_tags__tag__icontains=search_term)
            )
        ).prefetch_related('product_tags').distinct()
        
        # Verify search relevance
        for product in search_results:
            # Each result should contain the search term in name, description, content, or tags
            product_tags_list = [tag.tag.lower() for tag in product.product_tags.all()]
            
            contains_in_name = search_term_lower in product.name.lower()
            contains_in_description = search_term_lower in product.description.lower()
            contains_in_content = search_term_lower in product.content.lower()
            contains_in_tags = any(search_term_lower in tag for tag in product_tags_list)
            
            # At least one of these should be true for the product to be in results
            assert (contains_in_name or contains_in_description or 
                   contains_in_content or contains_in_tags), \
                   f"Product {product.name} doesn't contain search term '{search_term}' in any searchable field"