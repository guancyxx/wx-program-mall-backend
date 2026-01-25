from django.db import models


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








