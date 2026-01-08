"""
URL configuration for mall_server project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('apps.users.urls')),
    path('api/membership/', include('apps.membership.urls')),
    path('api/goods/', include('apps.products.urls')),  # Match Node.js /api/goods/ pattern
    path('api/products/', include('apps.products.urls')),  # RESTful API endpoint
    path('api/order/', include('apps.orders.urls')),  # Match Node.js /api/order/ pattern
    path('api/payments/', include('apps.payments.urls')),
    path('api/points/', include('apps.points.urls')),
    path('api/', include('apps.common.urls')),  # Include common URLs under /api/ prefix
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Serve static files from STATICFILES_DIRS in development
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()