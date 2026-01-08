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

    @staticmethod
    def generate_order_qr_code(order: Order) -> str:
        """Generate QR code for order verification (pickup orders)"""
        try:
            import qrcode
            from io import BytesIO
            import base64
            
            # Create QR code data - this should contain order verification info
            qr_data = {
                'roid': order.roid,
                'uid': order.uid.id,
                'amount': float(order.amount),
                'type': order.type,
                'verify_code': f"{order.roid}_{order.uid.id}"
            }
            
            # Convert to string format for QR code
            qr_string = f"ORDER_VERIFY:{order.roid}:{order.uid.id}:{order.amount}"
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_string)
            qr.make(fit=True)
            
            # Create QR code image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64 string
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            # Return data URL
            return f"data:image/png;base64,{img_str}"
            
        except ImportError:
            # If qrcode library is not available, return a placeholder URL
            return f"/api/order/qr/{order.roid}"
        except Exception as e:
            print(f"Failed to generate QR code for order {order.roid}: {e}")
            return f"/api/order/qr/{order.roid}"

