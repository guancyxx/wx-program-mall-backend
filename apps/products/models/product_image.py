from django.db import models


class ProductImage(models.Model):
    """Product images - replaces images array from Node.js"""
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='images')
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

