from django.db import models


class ProductTag(models.Model):
    """Product tags - replaces tags array from Node.js"""
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='product_tags')
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








