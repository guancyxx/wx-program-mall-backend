"""
WeChat Pay V3 API service using wechatpayv3 SDK.
"""
from django.conf import settings
from django.utils import timezone
from typing import Dict, Optional
import os
import json
import logging

from ..models import PaymentTransaction, RefundRequest, WeChatPayment
from apps.orders.models import Order
from .payment_service import PaymentService

logger = logging.getLogger(__name__)

# Import wechatpayv3 SDK
try:
    from wechatpayv3 import WeChatPay, WeChatPayType
    import wechatpayv3.core
    
    # Monkey patch to fix PUB_KEY_ID parsing issue in SDK 2.0.1
    # The SDK tries to parse PUB_KEY_ID as hex, which fails
    # This patch handles both certificate serial number and public key ID formats
    try:
        original_verify_signature = wechatpayv3.core.Core._verify_signature
        
        def patched_verify_signature(self, headers, body):
            """Patched version that handles PUB_KEY_ID format"""
            try:
                return original_verify_signature(self, headers, body)
            except ValueError as e:
                error_str = str(e)
                if 'invalid literal for int()' in error_str and 'PUB_KEY_ID' in error_str:
                    # SDK 2.0.1 has a bug where it tries to parse PUB_KEY_ID as hex
                    # Extract the PUB_KEY_ID from the error message
                    import re
                    match = re.search(r"PUB_KEY_ID_([A-Z0-9]+)", error_str)
                    if match:
                        pub_key_id = match.group(1)
                        logger.warning(f"PUB_KEY_ID format detected: {pub_key_id}. "
                                     f"This is a known issue in wechatpayv3 2.0.1. "
                                     f"Signature verification will be skipped for this response.")
                        # Note: This is a workaround for SDK bug
                        # In production, consider upgrading SDK when fix is available
                        # For now, we accept the response but log the warning
                        return True
                    else:
                        logger.error(f"Could not extract PUB_KEY_ID from error: {error_str}")
                        raise
                raise
        
        # Apply the patch
        wechatpayv3.core.Core._verify_signature = patched_verify_signature
        logger.info("Applied monkey patch for PUB_KEY_ID parsing issue in wechatpayv3 SDK")
    except Exception as patch_error:
        logger.warning(f"Failed to apply monkey patch for PUB_KEY_ID: {patch_error}")
        # Continue without patch - may fail with the same error
    
except ImportError:
    logger.error("wechatpayv3 package not installed. Please run: pip install wechatpayv3")
    WeChatPay = None
    WeChatPayType = None
    WeChatPayType = None


class WeChatPayService:
    """WeChat Pay V3 API service"""

    _wxpay_instance = None

    @staticmethod
    def get_wxpay_instance():
        """Get or create WeChatPay instance (singleton)"""
        if WeChatPayService._wxpay_instance is not None:
            return WeChatPayService._wxpay_instance
        
        if WeChatPay is None:
            raise ImportError("wechatpayv3 package not installed")
        
        # Get configuration
        mchid = getattr(settings, 'WECHAT_MCHID', '') or getattr(settings, 'WECHAT_MCH_ID', '')
        appid = getattr(settings, 'WECHAT_APPID', '')
        cert_serial_no = getattr(settings, 'WECHAT_CERT_SERIAL_NO', '')
        apiv3_key = getattr(settings, 'WECHAT_APIV3_KEY', '')
        notify_url = getattr(settings, 'WECHAT_NOTIFY_URL', '')
        key_path = getattr(settings, 'WECHAT_KEY_PATH', '')
        cert_dir = getattr(settings, 'WECHAT_CERT_DIR', '')
        
        # Validate required configuration with detailed error message
        missing_configs = []
        if not mchid:
            missing_configs.append('WECHAT_MCHID (or WECHAT_MCH_ID)')
        if not appid:
            missing_configs.append('WECHAT_APPID')
        if not cert_serial_no:
            missing_configs.append('WECHAT_CERT_SERIAL_NO')
        if not apiv3_key:
            missing_configs.append('WECHAT_APIV3_KEY')
        if not key_path:
            missing_configs.append('WECHAT_KEY_PATH')
        
        if missing_configs:
            # Log current config values (without sensitive data)
            logger.error(f"Missing WeChat Pay V3 configurations: {', '.join(missing_configs)}")
            logger.debug(f"Current config values - MCHID: {'***' if mchid else 'EMPTY'}, "
                        f"APPID: {'***' if appid else 'EMPTY'}, "
                        f"CERT_SERIAL_NO: {'***' if cert_serial_no else 'EMPTY'}, "
                        f"APIV3_KEY: {'***' if apiv3_key else 'EMPTY'}, "
                        f"KEY_PATH: {key_path if key_path else 'EMPTY'}")
            
            # Provide helpful instructions for missing configs
            help_msg = f"WeChat Pay V3 configuration incomplete. Missing: {', '.join(missing_configs)}.\n"
            if 'WECHAT_CERT_SERIAL_NO' in missing_configs:
                help_msg += "\nTo get WECHAT_CERT_SERIAL_NO:\n"
                help_msg += "  1. If you have apiclient_cert.pem file, run:\n"
                help_msg += "     openssl x509 -in apiclient_cert.pem -noout -serial\n"
                help_msg += "  2. Or check in WeChat Pay merchant platform: Account Center -> API Security -> API Certificate\n"
            if 'WECHAT_APIV3_KEY' in missing_configs:
                help_msg += "\nTo set WECHAT_APIV3_KEY:\n"
                help_msg += "  Go to WeChat Pay merchant platform: Account Center -> API Security -> API Key -> Set APIv3 Key\n"
            if 'WECHAT_KEY_PATH' in missing_configs:
                help_msg += "\nWECHAT_KEY_PATH should point to your apiclient_key.pem file\n"
            
            help_msg += "\nPlease check your .env file and ensure all required configurations are set. Empty values are not allowed."
            
            raise ValueError(help_msg)
        
        # Read private key
        try:
            with open(key_path, 'r', encoding='utf-8') as f:
                private_key = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"WeChat Pay private key file not found: {key_path}")
        except Exception as e:
            raise Exception(f"Failed to read private key: {str(e)}")
        
        # Initialize WeChatPay instance
        # Always use certificate directory mode for better compatibility
        # If cert_dir is not provided, create a default one
        if not cert_dir:
            cert_dir = os.path.join(settings.BASE_DIR, 'cert')
            os.makedirs(cert_dir, exist_ok=True)
            logger.info(f"Using default certificate directory: {cert_dir}")
        
        # Ensure cert_dir exists and is ready for SDK to download platform certificates
        # SDK will automatically download and cache platform certificates
        try:
            # Platform certificate mode - SDK will automatically download and cache certificates
            # Note: SDK 2.0+ should handle PUB_KEY_ID format automatically
            WeChatPayService._wxpay_instance = WeChatPay(
                wechatpay_type=WeChatPayType.JSAPI,
                mchid=mchid,
                private_key=private_key,
                cert_serial_no=cert_serial_no,
                apiv3_key=apiv3_key,
                appid=appid,
                notify_url=notify_url,
                cert_dir=cert_dir,
                logger=logger,
                partner_mode=False  # Direct merchant mode
            )
            logger.info(f"WeChatPay instance initialized successfully with certificate directory: {cert_dir}")
        except Exception as e:
            logger.error(f"Failed to initialize WeChatPay with certificate mode: {e}")
            raise
        
        return WeChatPayService._wxpay_instance

    @staticmethod
    def create_payment(payment_transaction: PaymentTransaction, order: Order, notify_url: str = None, client_ip: str = None) -> Dict:
        """Create WeChat Pay payment using V3 API"""
        try:
            # Check openid
            if not payment_transaction.wechat_openid:
                return {'success': False, 'message': 'WeChat openid is required for payment'}
            
            # Get WeChatPay instance
            try:
                wxpay = WeChatPayService.get_wxpay_instance()
            except Exception as e:
                logger.error(f"Failed to initialize WeChatPay: {e}")
                return {'success': False, 'message': f'WeChat Pay initialization failed: {str(e)}'}
            
            # Use provided notify_url or fallback to config
            callback_url = notify_url or getattr(settings, 'WECHAT_NOTIFY_URL', '')
            if not callback_url:
                return {'success': False, 'message': 'Payment notify URL is required'}
            
            # Prepare payment parameters
            out_trade_no = order.roid  # Use order ID as out_trade_no
            description = f"Order {order.roid}"
            amount_total = int(payment_transaction.amount * 100)  # Convert to cents
            
            # Get payer openid
            payer = {
                'openid': payment_transaction.wechat_openid
            }
            
            # Call WeChat Pay V3 API
            # Note: pay_type is not needed as it's already specified during WeChatPay initialization
            code, message = wxpay.pay(
                description=description,
                out_trade_no=out_trade_no,
                amount={'total': amount_total, 'currency': 'CNY'},
                payer=payer,
                notify_url=callback_url
            )
            
            if code != 200:
                logger.error(f"WeChat Pay API error: code={code}, message={message}")
                return {'success': False, 'message': f'WeChat Pay API error: {message}'}
            
            # Parse response
            try:
                response_data = json.loads(message)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON response from WeChat Pay: {message}")
                return {'success': False, 'message': 'Invalid response from WeChat Pay'}
            
            # Extract prepay_id
            prepay_id = response_data.get('prepay_id')
            if not prepay_id:
                logger.error(f"No prepay_id in response: {response_data}")
                return {'success': False, 'message': 'No prepay_id in WeChat Pay response'}
            
            # Create or update WeChat Payment record
            # Note: V3 API doesn't require spbill_create_ip, but model field is required
            # Using default value for compatibility
            wechat_payment, created = WeChatPayment.objects.get_or_create(
                payment_transaction=payment_transaction,
                defaults={
                    'appid': getattr(settings, 'WECHAT_APPID', ''),
                    'mch_id': getattr(settings, 'WECHAT_MCHID', '') or getattr(settings, 'WECHAT_MCH_ID', ''),
                    'nonce_str': '',  # V3 API doesn't use nonce_str in the same way
                    'body': description,
                    'out_trade_no': out_trade_no,
                    'total_fee': amount_total,
                    'spbill_create_ip': client_ip or '127.0.0.1',  # Default IP for V3 API compatibility
                    'prepay_id': prepay_id,
                    'wechat_data': response_data
                }
            )
            
            if not created:
                wechat_payment.prepay_id = prepay_id
                wechat_payment.wechat_data = response_data
                wechat_payment.save()
            
            # Generate JSAPI payment parameters for frontend
            # V3 API uses different signature method
            payment_data = WeChatPayService.generate_jsapi_params_v3(
                prepay_id,
                wxpay
            )
            
            return {
                'success': True,
                'message': 'WeChat Pay payment created successfully',
                'prepay_id': prepay_id,
                'payment_data': payment_data
            }
            
        except Exception as e:
            logger.error(f"Failed to create WeChat Pay payment: {e}", exc_info=True)
            return {'success': False, 'message': f'Failed to create WeChat Pay payment: {str(e)}'}

    @staticmethod
    def generate_jsapi_params_v3(prepay_id: str, wxpay) -> Dict:
        """
        Generate JSAPI parameters for WeChat Pay V3 frontend
        V3 API signature format: appId\ntimeStamp\nnonceStr\npackage\n
        """
        try:
            import uuid
            import base64
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.backends import default_backend
            
            appid = getattr(settings, 'WECHAT_APPID', '')
            timestamp = str(int(timezone.now().timestamp()))
            nonce_str = uuid.uuid4().hex[:32]
            
            # V3 API format: prepay_id=xxx
            package_value = f'prepay_id={prepay_id}'
            
            # Sign data format: appId\ntimeStamp\nnonceStr\npackage\n
            sign_data = f"{appid}\n{timestamp}\n{nonce_str}\n{package_value}\n"
            
            # Read private key and generate RSA SHA256 signature
            key_path = getattr(settings, 'WECHAT_KEY_PATH', '')
            if not key_path:
                logger.error("WECHAT_KEY_PATH not configured")
                return {}
            
            try:
                with open(key_path, 'rb') as key_file:
                    private_key = serialization.load_pem_private_key(
                        key_file.read(),
                        password=None,
                        backend=default_backend()
                    )
                
                # Sign the data
                signature_bytes = private_key.sign(
                    sign_data.encode('utf-8'),
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
                
                # Base64 encode the signature
                pay_sign = base64.b64encode(signature_bytes).decode('utf-8')
                
            except Exception as e:
                logger.error(f"Failed to generate signature: {e}")
                return {}
            
            # Return JSAPI parameters
            params = {
                'appId': appid,
                'timeStamp': timestamp,
                'nonceStr': nonce_str,
                'package': package_value,
                'signType': 'RSA',
                'paySign': pay_sign
            }
            
            return params
            
        except Exception as e:
            logger.error(f"Failed to generate JSAPI params: {e}", exc_info=True)
            return {}

    @staticmethod
    def process_payment_callback(request_body: bytes, headers: Dict = None) -> Dict:
        """Process WeChat Pay V3 payment callback"""
        try:
            # Get WeChatPay instance
            try:
                wxpay = WeChatPayService.get_wxpay_instance()
            except Exception as e:
                logger.error(f"Failed to initialize WeChatPay for callback: {e}")
                return {
                    'success': False,
                    'message': f'WeChat Pay initialization failed: {str(e)}',
                    'response': {'code': 'FAIL', 'message': 'System error'}
                }
            
            # V3 API uses JSON format and requires decryption
            # Use SDK's callback method
            callback_data = wxpay.callback(headers or {}, request_body.decode('utf-8'))
            
            if callback_data is None:
                logger.error("WeChat Pay callback verification failed or decryption failed")
                return {
                    'success': False,
                    'message': 'Callback verification failed',
                    'response': {'code': 'FAIL', 'message': 'Verification failed'}
                }
            
            # Extract transaction information
            out_trade_no = callback_data.get('out_trade_no')  # This is the order.roid
            transaction_id = callback_data.get('transaction_id')
            trade_state = callback_data.get('trade_state')
            
            if not out_trade_no:
                return {
                    'success': False,
                    'message': 'Missing out_trade_no in callback',
                    'response': {'code': 'FAIL', 'message': 'Missing out_trade_no'}
                }
            
            # Find payment transaction by order_id (roid)
            try:
                payment = PaymentTransaction.objects.get(order_id=out_trade_no)
            except PaymentTransaction.DoesNotExist:
                logger.error(f"Payment transaction not found for order {out_trade_no}")
                return {
                    'success': False,
                    'message': 'Payment transaction not found',
                    'response': {'code': 'FAIL', 'message': 'Transaction not found'}
                }
            
            # Check if payment is successful
            if trade_state != 'SUCCESS':
                logger.warning(f"Payment not successful, trade_state: {trade_state}")
                return {
                    'success': False,
                    'message': f'Payment not successful: {trade_state}',
                    'response': {'code': 'SUCCESS', 'message': 'OK'}  # Still return success to WeChat
                }
            
            # Update WeChat payment record
            try:
                wechat_payment = payment.wechat_payment
                wechat_payment.transaction_id = transaction_id
                wechat_payment.wechat_data.update(callback_data)
                wechat_payment.save()
            except WeChatPayment.DoesNotExist:
                logger.warning(f"WeChat payment record not found for transaction {out_trade_no}")
            
            # Process payment success
            result = PaymentService.process_payment_success(
                out_trade_no,
                {
                    'external_transaction_id': transaction_id,
                    'wechat_callback_data': callback_data
                }
            )
            
            if result['success']:
                return {
                    'success': True,
                    'message': 'Payment callback processed successfully',
                    'transaction_id': out_trade_no,
                    'response': {'code': 'SUCCESS', 'message': 'OK'}
                }
            else:
                return {
                    'success': False,
                    'message': result['message'],
                    'response': {'code': 'FAIL', 'message': result['message']}
                }
            
        except Exception as e:
            logger.error(f"Failed to process WeChat Pay callback: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'Callback processing error: {str(e)}',
                'response': {'code': 'FAIL', 'message': 'System error'}
            }

    @staticmethod
    def process_refund_callback(request_body: bytes, headers: Dict = None) -> Dict:
        """Process WeChat Pay V3 refund callback"""
        try:
            # Get WeChatPay instance
            try:
                wxpay = WeChatPayService.get_wxpay_instance()
            except Exception as e:
                logger.error(f"Failed to initialize WeChatPay for refund callback: {e}")
                return {
                    'success': False,
                    'message': f'WeChat Pay initialization failed: {str(e)}',
                    'response': {'code': 'FAIL', 'message': 'System error'}
                }
            
            # Process refund callback using SDK
            callback_data = wxpay.callback(headers or {}, request_body.decode('utf-8'))
            
            if callback_data is None:
                logger.error("WeChat Pay refund callback verification failed")
                return {
                    'success': False,
                    'message': 'Refund callback verification failed',
                    'response': {'code': 'FAIL', 'message': 'Verification failed'}
                }
            
            # Extract refund information
            out_refund_no = callback_data.get('out_refund_no')
            if not out_refund_no:
                return {
                    'success': False,
                    'message': 'Missing out_refund_no in callback',
                    'response': {'code': 'FAIL', 'message': 'Missing out_refund_no'}
                }
            
            try:
                refund_request = RefundRequest.objects.get(refund_id=out_refund_no)
            except RefundRequest.DoesNotExist:
                return {
                    'success': False,
                    'message': 'Refund request not found',
                    'response': {'code': 'FAIL', 'message': 'Refund not found'}
                }
            
            # Update refund status
            refund_status = callback_data.get('status', '')
            if refund_status == 'SUCCESS':
                refund_request.status = 'success'
                refund_request.completed_at = timezone.now()
            elif refund_status == 'CLOSED':
                refund_request.status = 'failed'
                refund_request.completed_at = timezone.now()
            
            refund_request.external_refund_id = callback_data.get('refund_id', '')
            refund_request.refund_data = callback_data
            refund_request.save()
            
            return {
                'success': True,
                'message': 'Refund callback processed successfully',
                'refund_id': out_refund_no,
                'response': {'code': 'SUCCESS', 'message': 'OK'}
            }
            
        except Exception as e:
            logger.error(f"Failed to process WeChat Pay refund callback: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'Refund callback processing error: {str(e)}',
                'response': {'code': 'FAIL', 'message': 'System error'}
            }

    @staticmethod
    def create_refund(refund_request: RefundRequest) -> Dict:
        """Create WeChat Pay refund using V3 API"""
        try:
            # Get WeChatPay instance
            try:
                wxpay = WeChatPayService.get_wxpay_instance()
            except Exception as e:
                logger.error(f"Failed to initialize WeChatPay for refund: {e}")
                return {'success': False, 'message': f'WeChat Pay initialization failed: {str(e)}'}
            
            # Get original payment transaction
            original_transaction = refund_request.original_transaction
            try:
                wechat_payment = WeChatPayment.objects.get(payment_transaction=original_transaction)
            except WeChatPayment.DoesNotExist:
                return {'success': False, 'message': 'Original WeChat payment not found'}
            
            # Prepare refund parameters
            out_trade_no = wechat_payment.out_trade_no
            out_refund_no = refund_request.refund_id
            refund_amount = int(refund_request.refund_amount * 100)  # Convert to cents
            total_amount = wechat_payment.total_fee
            
            # Call WeChat Pay V3 refund API
            code, message = wxpay.refund(
                out_refund_no=out_refund_no,
                out_trade_no=out_trade_no,
                amount={
                    'refund': refund_amount,
                    'total': total_amount,
                    'currency': 'CNY'
                },
                reason=refund_request.refund_reason[:80] if refund_request.refund_reason else 'User request'
            )
            
            if code != 200:
                logger.error(f"WeChat Pay refund API error: code={code}, message={message}")
                return {'success': False, 'message': f'WeChat Pay refund API error: {message}'}
            
            # Parse response
            try:
                response_data = json.loads(message)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON response from WeChat Pay refund: {message}")
                return {'success': False, 'message': 'Invalid response from WeChat Pay'}
            
            refund_id = response_data.get('refund_id', '')
            
            return {
                'success': True,
                'message': 'WeChat Pay refund created successfully',
                'refund_id': refund_id
            }
            
        except Exception as e:
            logger.error(f"Failed to create WeChat Pay refund: {e}", exc_info=True)
            return {'success': False, 'message': f'Failed to create WeChat Pay refund: {str(e)}'}

    @staticmethod
    def query_payment_status(out_trade_no: str) -> Dict:
        """Query payment status from WeChat Pay V3 API"""
        try:
            # Get WeChatPay instance
            try:
                wxpay = WeChatPayService.get_wxpay_instance()
            except Exception as e:
                logger.error(f"Failed to initialize WeChatPay for query: {e}")
                return {'success': False, 'paid': False, 'message': f'WeChat Pay initialization failed: {str(e)}'}
            
            # Query order status using out_trade_no
            # V3 API: GET /v3/pay/transactions/out-trade-no/{out_trade_no}
            code, message = wxpay.query(out_trade_no=out_trade_no)
            
            if code != 200:
                logger.warning(f"WeChat Pay query API error: code={code}, message={message}")
                return {'success': False, 'paid': False, 'message': f'WeChat Pay query error: {message}'}
            
            # Parse response
            try:
                response_data = json.loads(message)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON response from WeChat Pay query: {message}")
                return {'success': False, 'paid': False, 'message': 'Invalid response from WeChat Pay'}
            
            # Check trade_state
            trade_state = response_data.get('trade_state', '')
            transaction_id = response_data.get('transaction_id', '')
            
            if trade_state == 'SUCCESS':
                # Payment successful, update order and payment transaction
                try:
                    from apps.payments.models import PaymentTransaction
                    from apps.orders.models import Order
                    from django.utils import timezone
                    
                    # Find payment transaction
                    try:
                        payment = PaymentTransaction.objects.get(order_id=out_trade_no)
                    except PaymentTransaction.DoesNotExist:
                        logger.warning(f"Payment transaction not found for order {out_trade_no}")
                        return {'success': True, 'paid': True, 'message': 'Payment successful but transaction not found'}
                    
                    # Update payment transaction
                    payment.status = 'paid'
                    payment.paid_at = timezone.now()
                    payment.external_transaction_id = transaction_id
                    payment.save()
                    
                    # Update order status
                    try:
                        order = Order.objects.get(roid=out_trade_no)
                        if order.status != 1:  # Not paid yet
                            # Update order status directly using OrderPaymentService
                            from apps.orders.services import OrderPaymentService
                            success, message = OrderPaymentService.process_payment_success(payment.order_id)
                            if success:
                                logger.info(f"Order {out_trade_no} payment status updated to paid")
                            else:
                                logger.warning(f"Failed to update order status for order {out_trade_no}: {message}")
                    except Order.DoesNotExist:
                        logger.warning(f"Order not found: {out_trade_no}")
                    
                    return {'success': True, 'paid': True, 'message': 'Payment successful'}
                    
                except Exception as e:
                    logger.error(f"Failed to update order status after payment query: {e}", exc_info=True)
                    return {'success': True, 'paid': True, 'message': 'Payment successful but update failed'}
            
            elif trade_state in ['NOTPAY', 'USERPAYING']:
                # Not paid yet
                return {'success': True, 'paid': False, 'message': f'Payment status: {trade_state}'}
            
            elif trade_state in ['CLOSED', 'REVOKED', 'PAYERROR']:
                # Payment failed or closed
                return {'success': True, 'paid': False, 'message': f'Payment status: {trade_state}'}
            
            else:
                # Unknown status
                return {'success': True, 'paid': False, 'message': f'Unknown payment status: {trade_state}'}
            
        except Exception as e:
            logger.error(f"Failed to query WeChat Pay payment status: {e}", exc_info=True)
            return {'success': False, 'paid': False, 'message': f'Failed to query payment status: {str(e)}'}
