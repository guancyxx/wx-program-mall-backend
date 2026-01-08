"""
Order member benefits service for membership tier benefits and pricing.
"""
from decimal import Decimal
from typing import Dict, List, Tuple

from ..models import Order, OrderDiscount
from apps.users.models import User


class OrderMemberService:
    """Service for handling member benefits in orders"""

    @staticmethod
    def apply_member_benefits(order: Order) -> None:
        """Apply membership tier benefits to order"""
        try:
            user = order.uid
            
            # Get user's membership status
            try:
                from apps.membership.models import MembershipStatus
                membership_status = MembershipStatus.objects.select_related('tier').get(user=user)
            except MembershipStatus.DoesNotExist:
                # User has no membership status, skip benefits
                return
            
            tier = membership_status.tier
            tier_name = tier.name
            
            # Apply tier-based discount
            discount_rates = {
                'Silver': Decimal('0.05'),    # 5% discount
                'Gold': Decimal('0.10'),      # 10% discount
                'Platinum': Decimal('0.15'),  # 15% discount
            }
            
            if tier_name in discount_rates:
                discount_percentage = discount_rates[tier_name]
                discount_amount = order.amount * discount_percentage
                
                OrderDiscount.objects.create(
                    order=order,
                    discount_type='tier_discount',
                    discount_amount=discount_amount,
                    description=f'{tier_name} member discount ({discount_percentage * 100}%)',
                    discount_details={
                        'tier': tier_name,
                        'percentage': float(discount_percentage),
                        'original_amount': float(order.amount),
                        'discount_amount': float(discount_amount)
                    }
                )
                
                # Update order amount with discount
                order.amount -= discount_amount
                order.save()
            
            # Apply free shipping for Silver+ members (delivery orders only)
            if tier_name in ['Silver', 'Gold', 'Platinum'] and order.type == 2:
                # Assume standard shipping cost
                shipping_cost = Decimal('10.00')
                
                OrderDiscount.objects.create(
                    order=order,
                    discount_type='free_shipping',
                    discount_amount=shipping_cost,
                    description=f'Free shipping for {tier_name} members',
                    discount_details={
                        'tier': tier_name,
                        'shipping_cost_saved': float(shipping_cost)
                    }
                )
            
            # Early access notification for Gold/Platinum members
            if tier_name in ['Gold', 'Platinum']:
                # This would typically trigger notifications for new products
                # For now, just log the benefit
                OrderDiscount.objects.create(
                    order=order,
                    discount_type='promotion',
                    discount_amount=Decimal('0.00'),
                    description=f'{tier_name} member - Early access to new products',
                    discount_details={
                        'tier': tier_name,
                        'benefit_type': 'early_access'
                    }
                )
                
        except Exception as e:
            # Log error but don't fail order creation
            print(f"Failed to apply member benefits for order {order.roid}: {e}")
            import traceback
            traceback.print_exc()

    @staticmethod
    def get_member_pricing(user: User, goods_list: List[Dict]) -> List[Dict]:
        """Apply member-exclusive pricing to goods"""
        try:
            # Get user's membership status
            try:
                from apps.membership.models import MembershipStatus
                membership_status = MembershipStatus.objects.select_related('tier').get(user=user)
                tier_name = membership_status.tier.name
            except MembershipStatus.DoesNotExist:
                # No membership, return original pricing
                return goods_list
            
            # Apply member pricing
            updated_goods = []
            for item in goods_list:
                updated_item = item.copy()
                
                # Check if product has member-exclusive pricing
                # This would typically come from the product model
                original_price = Decimal(str(item['price']))
                
                # Apply tier-based pricing discounts
                if tier_name == 'Silver':
                    member_price = original_price * Decimal('0.95')  # 5% off
                elif tier_name == 'Gold':
                    member_price = original_price * Decimal('0.90')  # 10% off
                elif tier_name == 'Platinum':
                    member_price = original_price * Decimal('0.85')  # 15% off
                else:
                    member_price = original_price
                
                updated_item['original_price'] = float(original_price)
                updated_item['price'] = float(member_price)
                updated_item['member_discount'] = float(original_price - member_price)
                updated_item['tier'] = tier_name
                
                updated_goods.append(updated_item)
            
            return updated_goods
            
        except Exception as e:
            print(f"Failed to apply member pricing: {e}")
            return goods_list

    @staticmethod
    def check_member_exclusive_access(user: User, goods_list: List[Dict]) -> Tuple[bool, str]:
        """Check if user has access to member-exclusive products"""
        try:
            # Get user's membership status
            try:
                from apps.membership.models import MembershipStatus
                membership_status = MembershipStatus.objects.select_related('tier').get(user=user)
                tier_name = membership_status.tier.name
            except MembershipStatus.DoesNotExist:
                tier_name = 'Bronze'  # Default tier
            
            # Check each product for exclusive access requirements
            for item in goods_list:
                # This would typically check the product model for exclusivity settings
                # For now, simulate some products being exclusive to higher tiers
                gid = item.get('gid', '')
                
                # Convert gid to string safely - handle all types (int, str, None, etc.)
                try:
                    if gid is None:
                        gid_str = ''
                    elif isinstance(gid, str):
                        gid_str = gid
                    else:
                        gid_str = str(gid)
                except Exception:
                    gid_str = ''
                
                # Only check startswith if gid_str is a non-empty string
                if gid_str and isinstance(gid_str, str):
                    # Mock exclusive product check
                    if gid_str.startswith('exclusive_gold_') and tier_name not in ['Gold', 'Platinum']:
                        return False, f"Product {gid} requires Gold membership or higher"
                    elif gid_str.startswith('exclusive_platinum_') and tier_name != 'Platinum':
                        return False, f"Product {gid} requires Platinum membership"
            
            return True, ""
            
        except Exception as e:
            return False, f"Failed to check member access: {str(e)}"

    @staticmethod
    def apply_member_promotions(order: Order) -> None:
        """Apply member-specific promotions and offers"""
        try:
            user = order.uid
            
            # Get user's membership status
            try:
                from apps.membership.models import MembershipStatus
                membership_status = MembershipStatus.objects.select_related('tier').get(user=user)
                tier_name = membership_status.tier.name
            except MembershipStatus.DoesNotExist:
                return
            
            # Apply minimum order promotions
            if tier_name == 'Gold' and order.amount >= Decimal('100.00'):
                # Gold members get extra 5% off orders over $100
                extra_discount = order.amount * Decimal('0.05')
                OrderDiscount.objects.create(
                    order=order,
                    discount_type='promotion',
                    discount_amount=extra_discount,
                    description='Gold member bonus: 5% off orders over $100',
                    discount_details={
                        'tier': tier_name,
                        'promotion_type': 'minimum_order_bonus',
                        'minimum_amount': 100.00,
                        'bonus_percentage': 5.0
                    }
                )
                order.amount -= extra_discount
                order.save()
            
            elif tier_name == 'Platinum' and order.amount >= Decimal('50.00'):
                # Platinum members get extra 10% off orders over $50
                extra_discount = order.amount * Decimal('0.10')
                OrderDiscount.objects.create(
                    order=order,
                    discount_type='promotion',
                    discount_amount=extra_discount,
                    description='Platinum member bonus: 10% off orders over $50',
                    discount_details={
                        'tier': tier_name,
                        'promotion_type': 'minimum_order_bonus',
                        'minimum_amount': 50.00,
                        'bonus_percentage': 10.0
                    }
                )
                order.amount -= extra_discount
                order.save()
                
        except Exception as e:
            print(f"Failed to apply member promotions for order {order.roid}: {e}")

