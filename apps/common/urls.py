from django.urls import path
from .admin_views import (
    SalesReportView, MembershipReportView, InventoryReportView, 
    SecurityDashboardView, ReportExportView, dashboard_api, system_health_check
)
from .views.store_views import StoreListView, StoreDetailView
from apps.orders.views.admin_order_views import (
    AdminGetAllOrderView, AdminConfirmOrderView, AdminSendGoodsView,
    AdminWriteOffOrderView, AdminRefundView
)
from apps.users.views.admin_views import AdminGetUserListView
from apps.products.views.banner_views import SetHomeBannerView

app_name = 'common'

urlpatterns = [
    # Admin report views
    path('admin/reports/sales/', SalesReportView.as_view(), name='sales_report'),
    path('admin/reports/membership/', MembershipReportView.as_view(), name='membership_report'),
    path('admin/reports/inventory/', InventoryReportView.as_view(), name='inventory_report'),
    path('admin/reports/security/', SecurityDashboardView.as_view(), name='security_dashboard'),
    
    # Export endpoints
    path('admin/reports/export/<str:report_type>/<str:format_type>/', 
         ReportExportView.as_view(), name='report_export'),
    
    # API endpoints
    path('admin/api/dashboard/', dashboard_api, name='dashboard_api'),
    path('health/', system_health_check, name='health_check'),
    
    # Admin order management endpoints
    path('admin/getAllOrder/', AdminGetAllOrderView.as_view(), name='admin-get-all-order'),
    path('admin/confirmOrder/', AdminConfirmOrderView.as_view(), name='admin-confirm-order'),
    path('admin/sendGoods/', AdminSendGoodsView.as_view(), name='admin-send-goods'),
    path('admin/writeOffOrder/', AdminWriteOffOrderView.as_view(), name='admin-write-off-order'),
    path('admin/adminRefund/', AdminRefundView.as_view(), name='admin-refund'),
    
    # Admin user management endpoints
    path('admin/getUserList/', AdminGetUserListView.as_view(), name='admin-get-user-list'),
    
    # Admin banner management endpoints
    path('admin/setHomeBanner/', SetHomeBannerView.as_view(), name='admin-set-home-banner'),
    
    # Store endpoints
    path('stores/', StoreListView.as_view(), name='store_list'),
    path('stores/<int:pk>/', StoreDetailView.as_view(), name='store_detail'),
]