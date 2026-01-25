"""
Order payment processing service.
"""
from django.utils import timezone
from django.db import transaction
from typing import Tuple

from ..models import Order
from apps.points.services import PointsIntegrationService


class OrderPaymentService:
    """Service for handling order payment processing"""

    @staticmethod
    @transaction.atomic
    def process_payment_success(roid: str) -> Tuple[bool, str]:
        """Process successful payment for an order"""
        try:
            order = Order.objects.get(roid=roid)
            
            if order.status != -1:
                return False, "Order is not in pending payment status"
            
            # Update order status
            order.status = 1  # Paid
            order.pay_time = timezone.now()
            order.lock_timeout = None
            
            # Note: QR code is now generated on the frontend, no need to generate here
            
            order.save()
            
            # Award membership points
            try:
                PointsIntegrationService.handle_order_completion(
                    user=order.uid,
                    order_amount=order.amount,
                    order_id=roid,
                    is_first_purchase=False  # TODO: Implement first purchase detection
                )
            except Exception as e:
                # Log error but don't fail the payment processing
                print(f"Failed to award points for order {roid}: {e}")
            
            return True, "Payment processed successfully"
            
        except Order.DoesNotExist:
            return False, "Order not found"
        except Exception as e:
            return False, f"Failed to process payment: {str(e)}"

