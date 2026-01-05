from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone
from datetime import datetime, timedelta
from .reports import SalesReportGenerator, MembershipAnalytics, ProductAnalytics, ReportExporter
from .security import SecurityReportGenerator
import json


@method_decorator(staff_member_required, name='dispatch')
class SalesReportView(View):
    """Sales report admin view"""
    
    def get(self, request):
        """Display sales report page"""
        # Get date range from request
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        if request.GET.get('start_date'):
            try:
                start_date = datetime.strptime(request.GET['start_date'], '%Y-%m-%d')
                start_date = timezone.make_aware(start_date)
            except ValueError:
                pass
        
        if request.GET.get('end_date'):
            try:
                end_date = datetime.strptime(request.GET['end_date'], '%Y-%m-%d')
                end_date = timezone.make_aware(end_date)
            except ValueError:
                pass
        
        # Generate reports
        sales_summary = SalesReportGenerator.get_sales_summary(start_date, end_date)
        daily_sales = SalesReportGenerator.get_daily_sales(30)
        top_products = SalesReportGenerator.get_top_products(10, 30)
        sales_by_status = SalesReportGenerator.get_sales_by_status()
        
        context = {
            'title': 'Sales Performance Report',
            'sales_summary': sales_summary,
            'daily_sales': json.dumps(daily_sales),
            'top_products': top_products,
            'sales_by_status': sales_by_status,
            'start_date': start_date.date(),
            'end_date': end_date.date(),
        }
        
        return render(request, 'admin/reports/sales_report.html', context)


@method_decorator(staff_member_required, name='dispatch')
class MembershipReportView(View):
    """Membership analytics admin view"""
    
    def get(self, request):
        """Display membership report page"""
        # Generate membership analytics
        distribution = MembershipAnalytics.get_membership_distribution()
        upgrade_trends = MembershipAnalytics.get_tier_upgrade_trends(90)
        member_analysis = MembershipAnalytics.get_member_value_analysis()
        
        # Calculate summary statistics
        total_members = sum(tier['member_count'] for tier in distribution)
        total_spending = sum(tier['total_spending'] for tier in distribution)
        avg_spending_per_member = total_spending / total_members if total_members > 0 else 0
        
        context = {
            'title': 'Membership Analytics Dashboard',
            'distribution': distribution,
            'upgrade_trends': json.dumps(upgrade_trends),
            'member_analysis': member_analysis[:20],  # Top 20 members
            'summary': {
                'total_members': total_members,
                'total_spending': total_spending,
                'avg_spending_per_member': avg_spending_per_member,
            }
        }
        
        return render(request, 'admin/reports/membership_report.html', context)


@method_decorator(staff_member_required, name='dispatch')
class InventoryReportView(View):
    """Inventory and product analytics admin view"""
    
    def get(self, request):
        """Display inventory report page"""
        # Generate inventory and product reports
        inventory_report = ProductAnalytics.get_inventory_report()
        product_performance = ProductAnalytics.get_product_performance(30)
        
        context = {
            'title': 'Inventory & Product Analytics',
            'inventory_report': inventory_report,
            'product_performance': product_performance[:20],  # Top 20 products
            'low_stock_count': len(inventory_report['low_stock_products']),
            'out_of_stock_count': len(inventory_report['out_of_stock_products']),
        }
        
        return render(request, 'admin/reports/inventory_report.html', context)


@method_decorator(staff_member_required, name='dispatch')
class SecurityDashboardView(View):
    """Security monitoring dashboard"""
    
    def get(self, request):
        """Display security dashboard"""
        # Get security summary
        security_summary = SecurityReportGenerator.get_security_summary(7)
        security_risks = SecurityReportGenerator.get_top_security_risks()
        
        # Get recent audit logs
        from .models import AdminAuditLog
        recent_logs = AdminAuditLog.objects.select_related('user').order_by('-created_at')[:20]
        
        # Get system notifications
        from .models import SystemNotification
        active_notifications = SystemNotification.objects.filter(
            is_active=True,
            notification_type__in=['warning', 'error']
        ).order_by('-created_at')[:10]
        
        context = {
            'title': 'Security Monitoring Dashboard',
            'security_summary': security_summary,
            'security_risks': security_risks,
            'recent_logs': recent_logs,
            'active_notifications': active_notifications,
        }
        
        return render(request, 'admin/reports/security_dashboard.html', context)


@method_decorator(staff_member_required, name='dispatch')
class ReportExportView(View):
    """Export reports in various formats"""
    
    def get(self, request, report_type, format_type):
        """Export report data"""
        # Generate data based on report type
        if report_type == 'sales':
            data = self._get_sales_export_data(request)
            filename = f'sales_report_{timezone.now().strftime("%Y%m%d")}'
        elif report_type == 'membership':
            data = self._get_membership_export_data(request)
            filename = f'membership_report_{timezone.now().strftime("%Y%m%d")}'
        elif report_type == 'inventory':
            data = self._get_inventory_export_data(request)
            filename = f'inventory_report_{timezone.now().strftime("%Y%m%d")}'
        elif report_type == 'security':
            data = self._get_security_export_data(request)
            filename = f'security_report_{timezone.now().strftime("%Y%m%d")}'
        else:
            return JsonResponse({'error': 'Invalid report type'}, status=400)
        
        # Export in requested format
        if format_type == 'csv':
            content = ReportExporter.export_to_csv(data, filename)
            response = HttpResponse(content, content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        elif format_type == 'json':
            content = ReportExporter.export_to_json(data, filename)
            response = HttpResponse(content, content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename="{filename}.json"'
        else:
            return JsonResponse({'error': 'Invalid format type'}, status=400)
        
        return response
    
    def _get_sales_export_data(self, request):
        """Get sales data for export"""
        days = int(request.GET.get('days', 30))
        daily_sales = SalesReportGenerator.get_daily_sales(days)
        top_products = SalesReportGenerator.get_top_products(50, days)
        
        # Combine data for export
        export_data = []
        for day in daily_sales:
            export_data.append({
                'type': 'daily_sales',
                'date': day['date'],
                'orders': day['orders'],
                'revenue': day['revenue'],
            })
        
        for product in top_products:
            export_data.append({
                'type': 'top_product',
                'product_id': product['gid'],
                'product_name': product['product_name'],
                'total_revenue': product['total_revenue'],
                'total_quantity': product['total_quantity'],
                'order_count': product['order_count'],
            })
        
        return export_data
    
    def _get_membership_export_data(self, request):
        """Get membership data for export"""
        return MembershipAnalytics.get_member_value_analysis()
    
    def _get_inventory_export_data(self, request):
        """Get inventory data for export"""
        performance = ProductAnalytics.get_product_performance(30)
        return performance
    
    def _get_security_export_data(self, request):
        """Get security data for export"""
        from .models import AdminAuditLog
        
        days = int(request.GET.get('days', 7))
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        logs = AdminAuditLog.objects.filter(
            created_at__range=[start_date, end_date]
        ).select_related('user')
        
        export_data = []
        for log in logs:
            export_data.append({
                'timestamp': log.created_at.isoformat(),
                'user': log.user.username if log.user else 'Anonymous',
                'action': log.action,
                'model_name': log.model_name,
                'object_repr': log.object_repr,
                'message': log.message,
                'ip_address': log.ip_address,
            })
        
        return export_data


@staff_member_required
def dashboard_api(request):
    """API endpoint for dashboard data"""
    data_type = request.GET.get('type', 'summary')
    
    if data_type == 'summary':
        # Return summary statistics
        try:
            from apps.users.models import User
            from apps.orders.models import Order
            from apps.products.models import Product
            
            today = timezone.now().date()
            
            summary = {
                'users': {
                    'total': User.objects.count(),
                    'active': User.objects.filter(is_active=True).count(),
                    'new_today': User.objects.filter(created_at__date=today).count(),
                },
                'orders': {
                    'total': Order.objects.count(),
                    'today': Order.objects.filter(create_time__date=today).count(),
                    'pending': Order.objects.filter(status=0).count(),
                },
                'products': {
                    'total': Product.objects.count(),
                    'active': Product.objects.filter(status=1).count(),
                    'low_stock': Product.objects.filter(inventory__lte=10).count(),
                }
            }
            
            return JsonResponse(summary)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    elif data_type == 'sales_chart':
        # Return sales chart data
        days = int(request.GET.get('days', 7))
        daily_sales = SalesReportGenerator.get_daily_sales(days)
        return JsonResponse({'daily_sales': daily_sales})
    
    elif data_type == 'membership_chart':
        # Return membership distribution data
        distribution = MembershipAnalytics.get_membership_distribution()
        return JsonResponse({'distribution': distribution})
    
    elif data_type == 'security_summary':
        # Return security summary data
        summary = SecurityReportGenerator.get_security_summary(7)
        return JsonResponse(summary)
    
    else:
        return JsonResponse({'error': 'Invalid data type'}, status=400)


@staff_member_required
def system_health_check(request):
    """System health check endpoint"""
    health_status = {
        'timestamp': timezone.now().isoformat(),
        'status': 'healthy',
        'checks': {}
    }
    
    # Database connectivity check
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['checks']['database'] = 'ok'
    except Exception as e:
        health_status['checks']['database'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Check for critical issues
    try:
        from apps.products.models import Product
        from apps.orders.models import Order
        
        # Check for products with negative inventory
        negative_inventory = Product.objects.filter(inventory__lt=0).count()
        if negative_inventory > 0:
            health_status['checks']['inventory'] = f'warning: {negative_inventory} products with negative inventory'
        else:
            health_status['checks']['inventory'] = 'ok'
        
        # Check for stuck orders (pending payment for more than 24 hours)
        stuck_orders = Order.objects.filter(
            status=0,
            create_time__lt=timezone.now() - timedelta(hours=24)
        ).count()
        
        if stuck_orders > 0:
            health_status['checks']['orders'] = f'warning: {stuck_orders} orders stuck in pending payment'
        else:
            health_status['checks']['orders'] = 'ok'
        
    except Exception as e:
        health_status['checks']['business_logic'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    return JsonResponse(health_status)