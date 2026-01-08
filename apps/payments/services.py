from django.db import transaction
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import uuid
import hashlib
import xml.etree.ElementTree as ET
import requests
import logging
from typing import Dict, Optional, Tuple

from .models import PaymentMethod, PaymentTransaction, RefundRequest, WeChatPayment
from apps.orders.models import Order
from apps.orders.services import OrderPaymentService
from apps.common.wechat import generate_wechat_signature, verify_wechat_signature

logger = logging.getLogger(__name__)


class PaymentService:
    """Service class for payment operations"""

    @staticmethod
    @transaction.atomic
    def create_payment(user, order: Order, payment_method: str, return_url: str = None, notify_url: str = None) -> Dict:
        """Create payment transaction"""
        try:
            # Get payment method
            try:
                method = PaymentMethod.objects.get(name=payment_method, is_active=True)
            except PaymentMethod.DoesNotExist:
                return {'success': False, 'message': 'Invalid payment method'}
            
            # Create payment transaction
            payment_transaction = PaymentTransaction.objects.create(
                order_id=order.roid,
                user=user,
                payment_method=method,
                amount=order.amount,
                wechat_openid=getattr(user, 'wechat_openid', ''),
                payment_data={
                    'return_url': return_url,
                    'notify_url': notify_url,
                    'order_type': order.type,
                    'order_address': order.address
                }
            )
            
            # Process payment based on method
            if payment_method == 'wechat_pay':
                result = WeChatPayService.create_payment(payment_transaction, order)
                if not result['success']:
                    payment_transaction.status = 'failed'
                    payment_transaction.error_message = result['message']
                    payment_transaction.save()
                    return result
                
                # Update payment with WeChat Pay data
                payment_transaction.wechat_prepay_id = result.get('prepay_id', '')
                payment_transaction.external_transaction_id = result.get('prepay_id', '')
                payment_transaction.save()
                
                return {
                    'success': True,
                    'message': 'Payment created successfully',
                    'payment_transaction': payment_transaction,
                    'payment_data': result.get('payment_data', {})
                }
            
            else:
                return {'success': False, 'message': 'Payment method not implemented'}
            
        except Exception as e:
            logger.error(f"Failed to create payment: {e}")
            return {'success': False, 'message': f'Failed to create payment: {str(e)}'}

    @staticmethod
    @transaction.atomic
    def process_payment_success(transaction_id: str, external_data: Dict = None) -> Dict:
        """Process successful payment"""
        try:
            payment = PaymentTransaction.objects.get(transaction_id=transaction_id)
            
            if payment.status != 'pending':
                return {'success': False, 'message': 'Payment is not in pending status'}
            
            # Update payment status
            payment.status = 'success'
            payment.paid_at = timezone.now()
            
            if external_data:
                payment.external_transaction_id = external_data.get('external_transaction_id', payment.external_transaction_id)
                payment.callback_data = external_data
                payment.callback_received_at = timezone.now()
            
            payment.save()
            
            # Update order status
            success, message = OrderPaymentService.process_payment_success(payment.order_id)
            if not success:
                logger.error(f"Failed to update order status for payment {transaction_id}: {message}")
                # Don't fail the payment processing, just log the error
            
            return {'success': True, 'message': 'Payment processed successfully'}
            
        except PaymentTransaction.DoesNotExist:
            return {'success': False, 'message': 'Payment transaction not found'}
        except Exception as e:
            logger.error(f"Failed to process payment success: {e}")
            return {'success': False, 'message': f'Failed to process payment: {str(e)}'}

    @staticmethod
    @transaction.atomic
    def cancel_payment(payment: PaymentTransaction) -> Dict:
        """Cancel payment transaction"""
        try:
            if payment.status not in ['pending', 'processing']:
                return {'success': False, 'message': 'Payment cannot be cancelled in current status'}
            
            payment.status = 'cancelled'
            payment.save()
            
            return {'success': True, 'message': 'Payment cancelled successfully'}
            
        except Exception as e:
            logger.error(f"Failed to cancel payment: {e}")
            return {'success': False, 'message': f'Failed to cancel payment: {str(e)}'}

    @staticmethod
    @transaction.atomic
    def create_refund_request(transaction: PaymentTransaction, refund_amount: Decimal, 
                            refund_reason: str, refund_type: str = 'full', 
                            return_order_id: str = None) -> Dict:
        """Create refund request"""
        try:
            # Check if refund amount is valid
            if refund_amount > transaction.amount:
                return {'success': False, 'message': 'Refund amount exceeds original payment amount'}
            
            # Check for existing refunds
            existing_refunds = RefundRequest.objects.filter(
                original_transaction=transaction,
                status__in=['pending', 'processing', 'success']
            )
            
            total_refunded = sum(refund.refund_amount for refund in existing_refunds)
            if total_refunded + refund_amount > transaction.amount:
                return {'success': False, 'message': 'Total refund amount exceeds original payment amount'}
            
            # Create refund request
            refund_request = RefundRequest.objects.create(
                original_transaction=transaction,
                order_id=transaction.order_id,
                return_order_id=return_order_id,
                refund_type=refund_type,
                refund_amount=refund_amount,
                refund_reason=refund_reason
            )
            
            # Process refund based on payment method
            if transaction.payment_method.name == 'wechat_pay':
                result = WeChatPayService.create_refund(refund_request)
                if not result['success']:
                    refund_request.status = 'failed'
                    refund_request.error_message = result['message']
                    refund_request.save()
                    return result
                
                refund_request.external_refund_id = result.get('refund_id', '')
                refund_request.status = 'processing'
                refund_request.save()
            
            return {
                'success': True,
                'message': 'Refund request created successfully',
                'refund_request': refund_request
            }
            
        except Exception as e:
            logger.error(f"Failed to create refund request: {e}")
            return {'success': False, 'message': f'Failed to create refund request: {str(e)}'}


class WeChatPayService:
    """WeChat Pay specific service"""

    @staticmethod
    def get_config():
        """Get WeChat Pay configuration"""
        return {
            'appid': getattr(settings, 'WECHAT_APPID', ''),
            'mch_id': getattr(settings, 'WECHAT_MCH_ID', ''),
            'api_key': getattr(settings, 'WECHAT_API_KEY', ''),
            'notify_url': getattr(settings, 'WECHAT_NOTIFY_URL', ''),
            'api_base_url': 'https://api.mch.weixin.qq.com'
        }

    @staticmethod
    def create_payment(payment_transaction: PaymentTransaction, order: Order) -> Dict:
        """Create WeChat Pay payment"""
        try:
            config = WeChatPayService.get_config()
            
            if not all([config['appid'], config['mch_id'], config['api_key']]):
                return {'success': False, 'message': 'WeChat Pay configuration incomplete'}
            
            # Generate nonce string
            nonce_str = uuid.uuid4().hex[:32]
            
            # Prepare payment parameters
            params = {
                'appid': config['appid'],
                'mch_id': config['mch_id'],
                'nonce_str': nonce_str,
                'body': f"Order {order.roid}",
                'out_trade_no': payment_transaction.transaction_id,
                'total_fee': int(payment_transaction.amount * 100),  # Convert to cents
                'spbill_create_ip': '127.0.0.1',  # Should be actual client IP
                'notify_url': config['notify_url'],
                'trade_type': 'JSAPI',
                'openid': payment_transaction.wechat_openid
            }
            
            # Generate signature
            params['sign'] = generate_wechat_signature(params, config['api_key'])
            
            # Create WeChat Payment record
            wechat_payment = WeChatPayment.objects.create(
                payment_transaction=payment_transaction,
                appid=config['appid'],
                mch_id=config['mch_id'],
                nonce_str=nonce_str,
                body=params['body'],
                out_trade_no=params['out_trade_no'],
                total_fee=params['total_fee'],
                spbill_create_ip=params['spbill_create_ip'],
                sign=params['sign']
            )
            
            # Call WeChat Pay API
            xml_data = WeChatPayService.dict_to_xml(params)
            
            try:
                response = requests.post(
                    f"{config['api_base_url']}/pay/unifiedorder",
                    data=xml_data,
                    headers={'Content-Type': 'application/xml'},
                    timeout=30
                )
                
                result = WeChatPayService.xml_to_dict(response.text)
                
                if result.get('return_code') == 'SUCCESS' and result.get('result_code') == 'SUCCESS':
                    # Update WeChat payment record
                    wechat_payment.prepay_id = result.get('prepay_id', '')
                    wechat_payment.code_url = result.get('code_url', '')
                    wechat_payment.wechat_data = result
                    wechat_payment.save()
                    
                    # Generate payment data for frontend
                    payment_data = WeChatPayService.generate_jsapi_params(
                        config['appid'], 
                        result['prepay_id'], 
                        config['api_key']
                    )
                    
                    return {
                        'success': True,
                        'message': 'WeChat Pay payment created successfully',
                        'prepay_id': result['prepay_id'],
                        'payment_data': payment_data
                    }
                else:
                    error_msg = result.get('err_code_des', result.get('return_msg', 'Unknown error'))
                    return {'success': False, 'message': f'WeChat Pay error: {error_msg}'}
                
            except requests.RequestException as e:
                return {'success': False, 'message': f'WeChat Pay API error: {str(e)}'}
            
        except Exception as e:
            logger.error(f"Failed to create WeChat Pay payment: {e}")
            return {'success': False, 'message': f'Failed to create WeChat Pay payment: {str(e)}'}

    @staticmethod
    def create_refund(refund_request: RefundRequest) -> Dict:
        """Create WeChat Pay refund"""
        try:
            config = WeChatPayService.get_config()
            
            # Get original WeChat payment
            try:
                wechat_payment = WeChatPayment.objects.get(
                    payment_transaction=refund_request.original_transaction
                )
            except WeChatPayment.DoesNotExist:
                return {'success': False, 'message': 'Original WeChat payment not found'}
            
            # Generate nonce string
            nonce_str = uuid.uuid4().hex[:32]
            
            # Prepare refund parameters
            params = {
                'appid': config['appid'],
                'mch_id': config['mch_id'],
                'nonce_str': nonce_str,
                'out_trade_no': wechat_payment.out_trade_no,
                'out_refund_no': refund_request.refund_id,
                'total_fee': wechat_payment.total_fee,
                'refund_fee': int(refund_request.refund_amount * 100),  # Convert to cents
                'refund_desc': refund_request.refund_reason[:80]  # WeChat limit
            }
            
            # Generate signature
            params['sign'] = generate_wechat_signature(params, config['api_key'])
            
            # Call WeChat Pay refund API
            xml_data = WeChatPayService.dict_to_xml(params)
            
            try:
                # Note: WeChat Pay refund API requires client certificate
                # This is a simplified version - in production, you need to configure SSL certificates
                response = requests.post(
                    f"{config['api_base_url']}/secapi/pay/refund",
                    data=xml_data,
                    headers={'Content-Type': 'application/xml'},
                    timeout=30
                    # cert=(cert_path, key_path)  # Add SSL certificate in production
                )
                
                result = WeChatPayService.xml_to_dict(response.text)
                
                if result.get('return_code') == 'SUCCESS' and result.get('result_code') == 'SUCCESS':
                    return {
                        'success': True,
                        'message': 'WeChat Pay refund created successfully',
                        'refund_id': result.get('refund_id', '')
                    }
                else:
                    error_msg = result.get('err_code_des', result.get('return_msg', 'Unknown error'))
                    return {'success': False, 'message': f'WeChat Pay refund error: {error_msg}'}
                
            except requests.RequestException as e:
                return {'success': False, 'message': f'WeChat Pay refund API error: {str(e)}'}
            
        except Exception as e:
            logger.error(f"Failed to create WeChat Pay refund: {e}")
            return {'success': False, 'message': f'Failed to create WeChat Pay refund: {str(e)}'}

    @staticmethod
    def process_payment_callback(xml_data: bytes) -> Dict:
        """Process WeChat Pay payment callback"""
        try:
            config = WeChatPayService.get_config()
            
            # Parse XML data
            callback_data = WeChatPayService.xml_to_dict(xml_data.decode('utf-8'))
            
            # Verify signature
            sign = callback_data.pop('sign', '')
            if not verify_wechat_signature(callback_data, sign, config['api_key']):
                return {
                    'success': False,
                    'message': 'Invalid signature',
                    'response': '<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[Invalid signature]]></return_msg></xml>'
                }
            
            # Check return code
            if callback_data.get('return_code') != 'SUCCESS':
                return {
                    'success': False,
                    'message': f"WeChat callback error: {callback_data.get('return_msg', 'Unknown error')}",
                    'response': '<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[Process failed]]></return_msg></xml>'
                }
            
            # Check result code
            if callback_data.get('result_code') != 'SUCCESS':
                return {
                    'success': False,
                    'message': f"WeChat payment failed: {callback_data.get('err_code_des', 'Unknown error')}",
                    'response': '<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>'
                }
            
            # Get transaction
            out_trade_no = callback_data.get('out_trade_no')
            if not out_trade_no:
                return {
                    'success': False,
                    'message': 'Missing out_trade_no',
                    'response': '<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[Missing out_trade_no]]></return_msg></xml>'
                }
            
            try:
                payment = PaymentTransaction.objects.get(transaction_id=out_trade_no)
            except PaymentTransaction.DoesNotExist:
                return {
                    'success': False,
                    'message': 'Payment transaction not found',
                    'response': '<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[Transaction not found]]></return_msg></xml>'
                }
            
            # Update WeChat payment record
            try:
                wechat_payment = payment.wechat_payment
                wechat_payment.transaction_id = callback_data.get('transaction_id', '')
                wechat_payment.bank_type = callback_data.get('bank_type', '')
                wechat_payment.settlement_total_fee = callback_data.get('settlement_total_fee')
                wechat_payment.cash_fee = callback_data.get('cash_fee')
                wechat_payment.wechat_data.update(callback_data)
                wechat_payment.save()
            except WeChatPayment.DoesNotExist:
                logger.warning(f"WeChat payment record not found for transaction {out_trade_no}")
            
            # Process payment success
            result = PaymentService.process_payment_success(
                out_trade_no,
                {
                    'external_transaction_id': callback_data.get('transaction_id', ''),
                    'wechat_callback_data': callback_data
                }
            )
            
            if result['success']:
                return {
                    'success': True,
                    'message': 'Payment callback processed successfully',
                    'transaction_id': out_trade_no,
                    'response': '<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>'
                }
            else:
                return {
                    'success': False,
                    'message': result['message'],
                    'response': '<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[Process failed]]></return_msg></xml>'
                }
            
        except Exception as e:
            logger.error(f"Failed to process WeChat Pay callback: {e}")
            return {
                'success': False,
                'message': f'Callback processing error: {str(e)}',
                'response': '<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[System error]]></return_msg></xml>'
            }

    @staticmethod
    def process_refund_callback(xml_data: bytes) -> Dict:
        """Process WeChat Pay refund callback"""
        try:
            # Parse XML data
            callback_data = WeChatPayService.xml_to_dict(xml_data.decode('utf-8'))
            
            # Check return code
            if callback_data.get('return_code') != 'SUCCESS':
                return {
                    'success': False,
                    'message': f"WeChat refund callback error: {callback_data.get('return_msg', 'Unknown error')}",
                    'response': '<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[Process failed]]></return_msg></xml>'
                }
            
            # Get refund request
            out_refund_no = callback_data.get('out_refund_no')
            if not out_refund_no:
                return {
                    'success': False,
                    'message': 'Missing out_refund_no',
                    'response': '<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[Missing out_refund_no]]></return_msg></xml>'
                }
            
            try:
                refund_request = RefundRequest.objects.get(refund_id=out_refund_no)
            except RefundRequest.DoesNotExist:
                return {
                    'success': False,
                    'message': 'Refund request not found',
                    'response': '<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[Refund not found]]></return_msg></xml>'
                }
            
            # Update refund status
            refund_request.status = 'success'
            refund_request.completed_at = timezone.now()
            refund_request.external_refund_id = callback_data.get('refund_id', '')
            refund_request.refund_data = callback_data
            refund_request.save()
            
            return {
                'success': True,
                'message': 'Refund callback processed successfully',
                'refund_id': out_refund_no,
                'response': '<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>'
            }
            
        except Exception as e:
            logger.error(f"Failed to process WeChat Pay refund callback: {e}")
            return {
                'success': False,
                'message': f'Refund callback processing error: {str(e)}',
                'response': '<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[System error]]></return_msg></xml>'
            }

    @staticmethod
    def dict_to_xml(data: Dict) -> str:
        """Convert dictionary to XML format for WeChat Pay API"""
        xml_parts = ['<xml>']
        for key, value in data.items():
            xml_parts.append(f'<{key}><![CDATA[{value}]]></{key}>')
        xml_parts.append('</xml>')
        return ''.join(xml_parts)

    @staticmethod
    def xml_to_dict(xml_data: str) -> Dict:
        """Convert XML to dictionary for WeChat Pay response"""
        try:
            root = ET.fromstring(xml_data)
            result = {}
            for child in root:
                result[child.tag] = child.text
            return result
        except ET.ParseError:
            return {}

    @staticmethod
    def generate_jsapi_params(appid: str, prepay_id: str, api_key: str) -> Dict:
        """Generate JSAPI parameters for WeChat Pay frontend"""
        timestamp = str(int(timezone.now().timestamp()))
        nonce_str = uuid.uuid4().hex[:32]
        
        params = {
            'appId': appid,
            'timeStamp': timestamp,
            'nonceStr': nonce_str,
            'package': f'prepay_id={prepay_id}',
            'signType': 'MD5'
        }
        
        # Generate signature for JSAPI
        params['paySign'] = generate_wechat_signature(params, api_key)
        
        return params