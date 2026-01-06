from django.urls import path
from .admin_views import (
    SalesReportView, MembershipReportView, InventoryReportView, 
    SecurityDashboardView, ReportExportView, dashboard_api, system_health_check
)

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
]