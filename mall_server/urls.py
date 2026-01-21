"""
URL configuration for mall_server project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

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
    # OpenAPI documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Serve static files from STATICFILES_DIRS in development
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()