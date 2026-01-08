"""
Store/Live model for store locations.
Matches Node.js Live schema structure.
"""
from django.db import models
from django.utils import timezone


class Store(models.Model):
    """
    Store/Live model matching Node.js Live schema.
    Represents physical store locations for pickup orders.
    """
    
    # Store ID - using Django's default id field instead of custom lid
    # lid field removed - use id instead
    
    # Location (GeoJSON Point format: [longitude, latitude])
    # Stored as JSON to match Node.js structure
    location = models.JSONField(
        default=dict,
        help_text="GeoJSON Point: {type: 'Point', coordinates: [lng, lat]}"
    )
    
    # Basic information
    name = models.CharField(max_length=200, help_text="Store name")
    address = models.CharField(max_length=500, help_text="Store address")
    detail = models.CharField(max_length=500, blank=True, default='', help_text="Detailed address")
    phone = models.CharField(max_length=20, blank=True, default='', help_text="Store phone number")
    
    # Business hours
    start_time = models.CharField(max_length=20, blank=True, default='', help_text="Opening time (startTime in Node.js)")
    end_time = models.CharField(max_length=20, blank=True, default='', help_text="Closing time (endTime in Node.js)")
    
    # Status: 1=active, 2=deleted
    STATUS_CHOICES = [
        (1, 'Active'),
        (2, 'Deleted'),
    ]
    status = models.IntegerField(
        choices=STATUS_CHOICES,
        default=1,
        help_text="Store status: 1=active, 2=deleted"
    )
    
    # Image
    img = models.CharField(max_length=500, blank=True, default='', help_text="Store image URL")
    
    # Timestamps
    create_time = models.DateTimeField(
        auto_now_add=True,
        help_text="Creation time (createTime in Node.js)"
    )
    update_time = models.DateTimeField(
        auto_now=True,
        help_text="Last update time"
    )
    
    class Meta:
        db_table = 'stores'
        verbose_name = 'Store'
        verbose_name_plural = 'Stores'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['name']),
            models.Index(fields=['address']),
        ]
        ordering = ['-create_time']
    
    def __str__(self):
        return f"{self.name} (id: {self.id})"
    
    @property
    def is_active(self):
        """Check if store is active"""
        return self.status == 1
    
    def get_coordinates(self):
        """Get coordinates from location JSON"""
        if isinstance(self.location, dict):
            coords = self.location.get('coordinates', [])
            if len(coords) >= 2:
                return coords[0], coords[1]  # longitude, latitude
        return None, None
    
    def set_coordinates(self, longitude, latitude):
        """Set coordinates in GeoJSON Point format"""
        self.location = {
            'type': 'Point',
            'coordinates': [longitude, latitude]
        }
    
    def calculate_distance(self, lat, lon):
        """
        Calculate distance from given coordinates to store.
        Returns distance in kilometers.
        """
        import math
        
        store_lon, store_lat = self.get_coordinates()
        if store_lon is None or store_lat is None:
            return None
        
        # Haversine formula for distance calculation
        R = 6371  # Earth radius in kilometers
        
        dlat = math.radians(lat - store_lat)
        dlon = math.radians(lon - store_lon)
        
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(store_lat)) *
             math.cos(math.radians(lat)) *
             math.sin(dlon / 2) ** 2)
        
        c = 2 * math.asin(math.sqrt(a))
        distance = R * c
        
        return round(distance, 2)  # Round to 2 decimal places

