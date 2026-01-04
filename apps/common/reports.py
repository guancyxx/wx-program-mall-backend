from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json


class SalesReportGenerator:
    """Generate sales performance reports"""
    
    @staticmethod
    def get_sales_summary(start_date=None, end_date=None):
        """Get overall sales summary for a date range"""
        from apps.orders.models import Order
        
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        orders = Order.objects.filter(
            create_time__range=[start_date, end_date],
            status__in=[1, 2, 3, 4]  # Paid, Processing, Shipped, Delivered
        )
        
        summary = orders.aggregate(
            total_orders=Count('id'),
            total_revenue=Sum('amount'),
            average_order_value=Avg('amount'),
        )
        
        # Calculate conversion rate (paid orders vs all orders)
        all_orders = Order.objects.filter(create_time__range=[start_date, end_date])
        total_created = all_orders.count()
        conversion_rate = (summary['total_orders'] / total_created * 100) if total_created > 0 else 0
        
        summary.update({
            'conversion_rate': round(conversion_rate, 2),
            'period_start': start_date,
            'period_end': end_date,
        })
        
        return summary
    
    @staticmethod
    def get_daily_sales(days=30):
        """Get daily sales data for the last N days"""
        from apps.orders.models import Order
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        daily_sales = []
        current_date = start_date
        
        while current_date <= end_date:
            orders = Order.objects.filter(
                create_time__date=current_date,
                status__in=[1, 2, 3, 4]
            )
            
            day_summary = orders.aggregate(
                orders_count=Count('id'),
                revenue=Sum('amount')
            )
            
            daily_sales.append({
                'date': current_date.isoformat(),
                'orders': day_summary['orders_count'] or 0,
                'revenue': float(day_summary['revenue'] or 0),
            })
            
            current_date += timedelta(days=1)
        
        return daily_sales
    
    @staticmethod
    def get_top_products(limit=10, days=30):
        """Get top-selling products by revenue and quantity"""
        from apps.orders.models import OrderItem
        from apps.products.models import Product
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Top products by revenue
        top_by_revenue = OrderItem.objects.filter(
            order__create_time__range=[start_date, end_date],
            order__status__in=[1, 2, 3, 4]
        ).values('gid').annotate(
            total_revenue=Sum('amount'),
            total_quantity=Sum('quantity'),
            order_count=Count('order', distinct=True)
        ).order_by('-total_revenue')[:limit]
        
        # Enrich with product details
        for item in top_by_revenue:
            try:
                product = Product.objects.get(gid=item['gid'])
                item.update({
                    'product_name': product.name,
                    'product_price': float(product.price),
                    'current_inventory': product.inventory,
                })
            except Product.DoesNotExist:
                item.update({
                    'product_name': f"Product {item['gid']}",
                    'product_price': 0,
                    'current_inventory': 0,
                })
        
        return list(top_by_revenue)
    
    @staticmethod
    def get_sales_by_status():
        """Get order distribution by status"""
        from apps.orders.models import Order
        
        status_mapping = {
            -1: 'Cancelled',
            0: 'Pending Payment',
            1: 'Paid',
            2: 'Processing',
            3: 'Shipped',
            4: 'Delivered',
            5: 'Refunding',
            6: 'Refunded',
            7: 'Returned',
        }
        
        status_counts = Order.objects.values('status').annotate(
            count=Count('id'),
            revenue=Sum('amount')
        ).order_by('status')
        
        result = []
        for item in status_counts:
            result.append({
                'status': item['status'],
                'status_name': status_mapping.get(item['status'], f"Status {item['status']}"),
                'count': item['count'],
                'revenue': float(item['revenue'] or 0),
            })
        
        return result


class MembershipAnalytics:
    """Generate membership analytics and reports"""
    
    @staticmethod
    def get_membership_distribution():
        """Get distribution of members across tiers"""
        from apps.membership.models import MembershipTier, MembershipStatus
        
        distribution = MembershipTier.objects.annotate(
            member_count=Count('membershipstatus'),
            total_spending=Sum('membershipstatus__total_spending'),
            avg_spending=Avg('membershipstatus__total_spending')
        ).order_by('min_spending')
        
        result = []
        for tier in distribution:
            result.append({
                'tier_name': tier.display_name,
                'tier_code': tier.name,
                'member_count': tier.member_count,
                'total_spending': float(tier.total_spending or 0),
                'avg_spending': float(tier.avg_spending or 0),
                'points_multiplier': float(tier.points_multiplier),
                'min_spending': float(tier.min_spending),
                'max_spending': float(tier.max_spending) if tier.max_spending else None,
            })
        
        return result
    
    @staticmethod
    def get_tier_upgrade_trends(days=90):
        """Get tier upgrade trends over time"""
        from apps.membership.models import TierUpgradeLog
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        upgrades = TierUpgradeLog.objects.filter(
            created_at__range=[start_date, end_date]
        ).select_related('from_tier', 'to_tier')
        
        # Group by week
        weekly_upgrades = {}
        for upgrade in upgrades:
            week_start = upgrade.created_at.date() - timedelta(days=upgrade.created_at.weekday())
            week_key = week_start.isoformat()
            
            if week_key not in weekly_upgrades:
                weekly_upgrades[week_key] = {
                    'week_start': week_key,
                    'total_upgrades': 0,
                    'by_tier': {}
                }
            
            weekly_upgrades[week_key]['total_upgrades'] += 1
            
            tier_key = f"{upgrade.from_tier.name if upgrade.from_tier else 'new'}_to_{upgrade.to_tier.name}"
            if tier_key not in weekly_upgrades[week_key]['by_tier']:
                weekly_upgrades[week_key]['by_tier'][tier_key] = 0
            weekly_upgrades[week_key]['by_tier'][tier_key] += 1
        
        return list(weekly_upgrades.values())
    
    @staticmethod
    def get_member_value_analysis():
        """Analyze member value by tier"""
        from apps.membership.models import MembershipStatus
        from apps.orders.models import Order
        from apps.points.models import PointsAccount
        
        analysis = []
        
        for membership in MembershipStatus.objects.select_related('tier', 'user').all():
            # Get user's order statistics
            user_orders = Order.objects.filter(
                uid=membership.user,
                status__in=[1, 2, 3, 4]
            )
            
            order_stats = user_orders.aggregate(
                total_orders=Count('id'),
                total_spent=Sum('amount'),
                avg_order_value=Avg('amount')
            )
            
            # Get points information
            try:
                points_account = membership.user.points_account
                points_data = {
                    'available_points': points_account.available_points,
                    'lifetime_earned': points_account.lifetime_earned,
                    'lifetime_redeemed': points_account.lifetime_redeemed,
                }
            except:
                points_data = {
                    'available_points': 0,
                    'lifetime_earned': 0,
                    'lifetime_redeemed': 0,
                }
            
            analysis.append({
                'user_id': membership.user.id,
                'username': membership.user.username,
                'tier': membership.tier.display_name,
                'tier_code': membership.tier.name,
                'total_spending': float(membership.total_spending),
                'tier_start_date': membership.tier_start_date.isoformat(),
                'order_count': order_stats['total_orders'] or 0,
                'order_total': float(order_stats['total_spent'] or 0),
                'avg_order_value': float(order_stats['avg_order_value'] or 0),
                **points_data,
            })
        
        return analysis


class ProductAnalytics:
    """Generate product analytics and inventory reports"""
    
    @staticmethod
    def get_inventory_report():
        """Get comprehensive inventory report"""
        from apps.products.models import Product
        
        products = Product.objects.select_related('category').all()
        
        report = {
            'summary': {
                'total_products': products.count(),
                'active_products': products.filter(status=1).count(),
                'out_of_stock': products.filter(inventory=0).count(),
                'low_stock': products.filter(inventory__lte=10, inventory__gt=0).count(),
                'total_inventory_value': 0,
            },
            'categories': {},
            'low_stock_products': [],
            'out_of_stock_products': [],
        }
        
        total_value = Decimal('0')
        
        for product in products:
            # Calculate inventory value
            inventory_value = product.inventory * product.price
            total_value += inventory_value
            
            # Category analysis
            category_name = product.category.name if product.category else 'Uncategorized'
            if category_name not in report['categories']:
                report['categories'][category_name] = {
                    'product_count': 0,
                    'total_inventory': 0,
                    'total_value': 0,
                    'avg_price': 0,
                }
            
            report['categories'][category_name]['product_count'] += 1
            report['categories'][category_name]['total_inventory'] += product.inventory
            report['categories'][category_name]['total_value'] += float(inventory_value)
            
            # Low stock and out of stock tracking
            if product.inventory == 0:
                report['out_of_stock_products'].append({
                    'gid': product.gid,
                    'name': product.name,
                    'category': category_name,
                    'price': float(product.price),
                    'sold': product.sold,
                })
            elif product.inventory <= 10:
                report['low_stock_products'].append({
                    'gid': product.gid,
                    'name': product.name,
                    'category': category_name,
                    'inventory': product.inventory,
                    'price': float(product.price),
                    'sold': product.sold,
                })
        
        # Calculate category averages
        for category_data in report['categories'].values():
            if category_data['product_count'] > 0:
                category_data['avg_price'] = category_data['total_value'] / category_data['product_count']
        
        report['summary']['total_inventory_value'] = float(total_value)
        
        return report
    
    @staticmethod
    def get_product_performance(days=30):
        """Get product performance metrics"""
        from apps.products.models import Product
        from apps.orders.models import OrderItem
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get sales data for the period
        sales_data = OrderItem.objects.filter(
            order__create_time__range=[start_date, end_date],
            order__status__in=[1, 2, 3, 4]
        ).values('gid').annotate(
            units_sold=Sum('quantity'),
            revenue=Sum('amount'),
            order_count=Count('order', distinct=True)
        )
        
        # Create lookup dictionary
        sales_lookup = {item['gid']: item for item in sales_data}
        
        performance = []
        for product in Product.objects.select_related('category').all():
            sales_info = sales_lookup.get(product.gid, {
                'units_sold': 0,
                'revenue': 0,
                'order_count': 0
            })
            
            # Calculate performance metrics
            inventory_turnover = 0
            if product.inventory > 0:
                inventory_turnover = sales_info['units_sold'] / product.inventory
            
            performance.append({
                'gid': product.gid,
                'name': product.name,
                'category': product.category.name if product.category else 'Uncategorized',
                'price': float(product.price),
                'inventory': product.inventory,
                'total_sold': product.sold,
                'period_sold': sales_info['units_sold'],
                'period_revenue': float(sales_info['revenue']),
                'period_orders': sales_info['order_count'],
                'inventory_turnover': round(inventory_turnover, 2),
                'views': product.views,
                'is_featured': product.has_recommend,
                'is_top': product.has_top,
            })
        
        # Sort by period revenue
        performance.sort(key=lambda x: x['period_revenue'], reverse=True)
        
        return performance


class ReportExporter:
    """Export reports in various formats"""
    
    @staticmethod
    def export_to_csv(data, filename):
        """Export data to CSV format"""
        import csv
        import io
        
        if not data:
            return None
        
        output = io.StringIO()
        
        # Get field names from first item
        fieldnames = data[0].keys()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in data:
            writer.writerow(row)
        
        return output.getvalue()
    
    @staticmethod
    def export_to_json(data, filename):
        """Export data to JSON format"""
        return json.dumps(data, indent=2, default=str)
    
    @staticmethod
    def generate_report_summary(report_type, data):
        """Generate a summary for any report"""
        summary = {
            'report_type': report_type,
            'generated_at': timezone.now().isoformat(),
            'record_count': len(data) if isinstance(data, list) else 1,
        }
        
        if report_type == 'sales':
            if isinstance(data, dict) and 'total_revenue' in data:
                summary['total_revenue'] = data['total_revenue']
                summary['total_orders'] = data['total_orders']
        elif report_type == 'membership':
            if isinstance(data, list):
                summary['total_members'] = sum(item.get('member_count', 0) for item in data)
        elif report_type == 'inventory':
            if isinstance(data, dict) and 'summary' in data:
                summary.update(data['summary'])
        
        return summary