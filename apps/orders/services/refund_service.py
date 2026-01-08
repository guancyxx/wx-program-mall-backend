"""
Refund service for processing order refunds.
"""
from django.db import transaction
from typing import Tuple

from ..models import Order, OrderItem, ReturnOrder
from apps.users.models import User


class RefundService:
    """Service class for refund operations"""

    @staticmethod
    @transaction.atomic
    def process_refund_request(user: User, roid: str, rrid: str, reason: str) -> Tuple[bool, str]:
        """Process refund request for an order item"""
        try:
            # Get order
            order = Order.objects.get(roid=roid, uid=user)
            
            # Check if order supports refund
            if order.status in [-1, 2, 3, 4, 5, 7]:
                return False, "This order does not support refund"
            
            # Get return order
            return_order = ReturnOrder.objects.get(rrid=rrid, uid=user, roid=roid)
            
            if return_order.status != -1:
                return False, "Return order status is invalid"
            
            # TODO: Implement actual WeChat Pay refund API call
            # For now, simulate successful refund
            refund_success = True
            
            if not refund_success:
                return False, "Refund failed"
            
            # Update order status
            order.status = 6  # Partial refund
            return_order.status = 1  # Completed
            
            # Update order item
            order_item = OrderItem.objects.get(rrid=rrid)
            order_item.is_return = True
            order_item.save()
            
            # Check if all items are returned
            all_returned = all(item.is_return for item in order.items.all())
            if all_returned:
                order.status = 4  # Full refund
            
            order.save()
            return_order.save()
            
            return True, "Refund processed successfully"
            
        except Order.DoesNotExist:
            return False, "Order not found"
        except ReturnOrder.DoesNotExist:
            return False, "Return order not found"
        except Exception as e:
            return False, f"Failed to process refund: {str(e)}"

