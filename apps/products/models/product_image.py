from django.db import models
import os
from pathlib import Path


def product_image_upload_path(instance, filename):
    """Generate upload path for product images"""
    # Extract extension
    ext = filename.split('.')[-1]
    # Generate filename based on product name and order
    if instance.product:
        product_name = instance.product.name.replace(' ', '_').replace('/', '_')[:20]
    else:
        product_name = 'product'
    order = instance.order if instance.order else 0
    new_filename = f"{order:02d}_{product_name}.{ext}"
    return os.path.join('beef', new_filename)


class ProductImage(models.Model):
    """Product images - replaces images array from Node.js"""
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=product_image_upload_path, blank=True, null=True, help_text="Upload image file")
    image_url = models.CharField(max_length=500, blank=True, help_text="Image URL (auto-filled from uploaded image or manual entry)")
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0, help_text="Display order")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        # Save first to get the image path
        super().save(*args, **kwargs)
        
        # If image is uploaded and image_url is not set, copy to static directory
        if self.image and (not self.image_url or self.image_url == ''):
            from django.conf import settings
            import shutil
            
            # Copy uploaded file to static/beef/ directory
            static_beef_dir = Path(settings.BASE_DIR) / 'static' / 'beef'
            static_beef_dir.mkdir(parents=True, exist_ok=True)
            
            # Get filename from uploaded image
            filename = os.path.basename(self.image.name)
            # Generate static path
            static_path = static_beef_dir / filename
            
            # Copy file to static directory
            if hasattr(self.image, 'path') and self.image.path and os.path.exists(self.image.path):
                shutil.copy2(self.image.path, static_path)
                # Update image_url to static path
                self.image_url = f'/static/beef/{filename}'
                # Save again to update image_url (avoid recursion)
                super().save(update_fields=['image_url'])

    class Meta:
        db_table = 'product_images'
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['product', 'is_primary']),
            models.Index(fields=['product', 'order']),
        ]

    def __str__(self):
        return f"Image for {self.product.name}"

