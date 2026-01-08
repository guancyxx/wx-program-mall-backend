"""
Member benefits preview views.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal

from apps.common.utils import success_response, error_response
from ..serializers import OrderCreateSerializer
from ..services import OrderService, OrderMemberService


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def preview_member_benefits(request):
    """Preview member benefits for order before creation"""
    try:
        serializer = OrderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid order data", serializer.errors)

        goods_list = serializer.validated_data['goods']
        
        # Check member access
        has_access, access_msg = OrderMemberService.check_member_exclusive_access(request.user, goods_list)
        if not has_access:
            return error_response(access_msg)

        # Get member pricing
        goods_with_pricing = OrderMemberService.get_member_pricing(request.user, goods_list)
        
        # Calculate totals
        original_total = OrderService.calculate_order_total(goods_list)
        member_total = OrderService.calculate_order_total(goods_with_pricing)
        
        # Get user's membership info
        try:
            from apps.membership.models import MembershipStatus
            membership_status = MembershipStatus.objects.select_related('tier').get(user=request.user)
            tier_name = membership_status.tier.name
        except MembershipStatus.DoesNotExist:
            tier_name = 'Bronze'

        # Calculate potential additional discounts
        additional_discounts = []
        
        if tier_name in ['Silver', 'Gold', 'Platinum']:
            discount_rates = {
                'Silver': 0.05,
                'Gold': 0.10,
                'Platinum': 0.15
            }
            tier_discount = member_total * Decimal(str(discount_rates[tier_name]))
            additional_discounts.append({
                'type': 'tier_discount',
                'description': f'{tier_name} member discount ({discount_rates[tier_name] * 100}%)',
                'amount': float(tier_discount)
            })

        # Free shipping benefit
        if tier_name in ['Silver', 'Gold', 'Platinum'] and serializer.validated_data['type'] == 2:
            additional_discounts.append({
                'type': 'free_shipping',
                'description': f'Free shipping for {tier_name} members',
                'amount': 10.00  # Standard shipping cost
            })

        # Calculate final total
        total_discount = sum(discount['amount'] for discount in additional_discounts)
        final_total = float(member_total) - total_discount

        return success_response({
            'tier': tier_name,
            'pricing_preview': {
                'original_total': float(original_total),
                'member_pricing_total': float(member_total),
                'member_pricing_savings': float(original_total - member_total),
                'additional_discounts': additional_discounts,
                'total_discount': total_discount,
                'final_total': max(0, final_total)  # Ensure non-negative
            },
            'goods_with_member_pricing': goods_with_pricing,
            'benefits_summary': {
                'has_member_pricing': float(original_total) > float(member_total),
                'has_tier_discount': tier_name in ['Silver', 'Gold', 'Platinum'],
                'has_free_shipping': tier_name in ['Silver', 'Gold', 'Platinum'] and serializer.validated_data['type'] == 2,
                'total_savings': float(original_total) - final_total
            }
        }, 'Member benefits preview generated')

    except Exception as e:
        return error_response(f"Server error: {str(e)}")

