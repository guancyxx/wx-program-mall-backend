from django.urls import path
from . import views

# URL patterns matching Node.js API exactly
urlpatterns = [
    # User-facing endpoints (matching /api/goods/ from Node.js)
    path('getGoodsList/', views.ProductListView.as_view(), name='product-list'),
    path('getGoodsDetail/', views.ProductDetailView.as_view(), name='product-detail'),
    path('search/', views.product_search, name='product-search'),
    
    # Member-exclusive endpoints (new functionality)
    path('member-exclusive/', views.member_exclusive_products, name='member-exclusive-products'),
    
    # Admin endpoints (matching /api/goods/ from Node.js)
    path('create/', views.ProductCreateView.as_view(), name='product-create'),
    path('updateGoods/', views.ProductUpdateView.as_view(), name='product-update'),
    path('adminGetGoodslist/', views.AdminProductListView.as_view(), name='admin-product-list'),
]