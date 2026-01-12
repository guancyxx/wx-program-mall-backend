from django.urls import path
from . import views

# URL patterns
# RESTful API endpoints (/api/products/) are the standard way to access products
urlpatterns = [
    # Search endpoint
    path('search/', views.product_search, name='product-search'),
    
    # Member-exclusive endpoints
    path('member-exclusive/', views.member_exclusive_products, name='member-exclusive-products'),
    
    # Admin endpoints
    path('create/', views.ProductCreateView.as_view(), name='product-create'),
    path('updateGoods/', views.ProductUpdateView.as_view(), name='product-update'),
    path('adminGetGoodslist/', views.AdminProductListView.as_view(), name='admin-product-list'),
    
    # Banner endpoints
    path('getBanners/', views.GetBannersView.as_view(), name='get-banners'),
    
    # RESTful API endpoints (for /api/products/)
    # GET /api/products/ - List products
    # GET /api/products/{id}/ - Get product detail by Django id (primary key)
    # Must be last to avoid conflicts with other paths
    path('<int:id>/', views.ProductDetailView.as_view(), name='product-detail-restful'),
    path('', views.ProductListView.as_view(), name='product-list-restful'),
]