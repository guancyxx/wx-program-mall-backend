"""
Middleware for API compatibility with Node.js frontend and security
"""

import json
import logging
import time
from django.http import JsonResponse, HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.conf import settings
from rest_framework.renderers import JSONRenderer
from .security import SecurityMonitor, SecurityAuditLogger

logger = logging.getLogger(__name__)


class SecurityMiddleware(MiddlewareMixin):
    """
    Comprehensive security middleware for rate limiting, security headers, and threat detection
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def __call__(self, request):
        # Pre-process security checks
        if self._is_rate_limited(request):
            return self._rate_limit_response(request)
        
        # Process request
        response = self.get_response(request)
        
        # Add security headers
        self._add_security_headers(response)
        
        return response
    
    def _is_rate_limited(self, request):
        """Check if request should be rate limited"""
        ip_address = self._get_client_ip(request)
        user_id = getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None
        
        # Define rate limits for different endpoints
        rate_limits = {
            '/api/users/login': {'limit': 5, 'window': 300},  # 5 attempts per 5 minutes
            '/api/users/register': {'limit': 3, 'window': 3600},  # 3 registrations per hour
            '/api/users/passwordLogin': {'limit': 5, 'window': 300},  # 5 attempts per 5 minutes
            '/api/order/createOrder': {'limit': 10, 'window': 60},  # 10 orders per minute
            '/api/payments/': {'limit': 20, 'window': 60},  # 20 payment requests per minute
            '/admin/': {'limit': 100, 'window': 60},  # 100 admin requests per minute
        }
        
        # Default rate limit for API endpoints
        default_api_limit = {'limit': 1000, 'window': 60}  # 1000 requests per minute
        
        # Find matching rate limit
        rate_limit = None
        for path_prefix, limit_config in rate_limits.items():
            if request.path.startswith(path_prefix):
                rate_limit = limit_config
                break
        
        if not rate_limit and request.path.startswith('/api/'):
            rate_limit = default_api_limit
        
        if not rate_limit:
            return False  # No rate limiting for non-API paths
        
        # Create cache keys for IP and user-based limiting
        ip_cache_key = f"rate_limit:ip:{ip_address}:{request.path}"
        user_cache_key = f"rate_limit:user:{user_id}:{request.path}" if user_id else None
        
        # Check IP-based rate limit
        ip_requests = cache.get(ip_cache_key, 0)
        if ip_requests >= rate_limit['limit']:
            return True
        
        # Check user-based rate limit (if authenticated)
        if user_cache_key:
            user_requests = cache.get(user_cache_key, 0)
            if user_requests >= rate_limit['limit']:
                return True
        
        # Increment counters
        cache.set(ip_cache_key, ip_requests + 1, rate_limit['window'])
        if user_cache_key:
            user_requests = cache.get(user_cache_key, 0)
            cache.set(user_cache_key, user_requests + 1, rate_limit['window'])
        
        return False
    
    def _rate_limit_response(self, request):
        """Return rate limit exceeded response"""
        ip_address = self._get_client_ip(request)
        user = getattr(request, 'user', None) if hasattr(request, 'user') else None
        
        # Log rate limit violation
        SecurityMonitor.log_security_event(
            'RATE_LIMIT_EXCEEDED',
            user=user,
            ip_address=ip_address,
            details=f"Rate limit exceeded for {request.path} from {ip_address}"
        )
        
        # Return Node.js compatible error response
        error_response = {
            'code': 42901,  # Rate limit error code
            'msg': '请求过于频繁，请稍后再试',
            'data': None
        }
        
        response = JsonResponse(error_response, status=429)
        response['Retry-After'] = '60'  # Suggest retry after 60 seconds
        return response
    
    def _add_security_headers(self, response):
        """Add security headers to response"""
        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Enable XSS protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Content Security Policy (basic)
        response['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        
        # HSTS (only in production)
        if not getattr(settings, 'DEBUG', True):
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Remove server information
        if 'Server' in response:
            del response['Server']
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip


class ErrorHandlingMiddleware(MiddlewareMixin):
    """
    Secure error handling middleware that prevents information leakage
    """
    
    def process_exception(self, request, exception):
        """Handle exceptions securely"""
        # Log the actual exception for debugging
        logger.error(f"Exception in {request.path}: {str(exception)}", exc_info=True)
        
        # Log security event for potential attacks
        if self._is_potential_attack(exception):
            SecurityMonitor.log_security_event(
                'POTENTIAL_ATTACK',
                user=getattr(request, 'user', None) if hasattr(request, 'user') else None,
                ip_address=SecurityMiddleware(None)._get_client_ip(request),
                details=f"Potential attack detected: {type(exception).__name__} in {request.path}"
            )
        
        # Return generic error response without exposing internal details
        if request.path.startswith('/api/'):
            error_response = {
                'code': 50001,
                'msg': '服务器内部错误，请稍后重试',
                'data': None
            }
            return JsonResponse(error_response, status=500)
        
        return None  # Let Django handle non-API errors normally
    
    def _is_potential_attack(self, exception):
        """Detect if exception might indicate an attack"""
        attack_indicators = [
            'DoesNotExist',  # Potential enumeration attack
            'ValidationError',  # Potential injection attempt
            'PermissionDenied',  # Potential privilege escalation
            'SuspiciousOperation',  # Django's built-in security exception
        ]
        
        exception_name = type(exception).__name__
        return any(indicator in exception_name for indicator in attack_indicators)


class NodeJSCompatibilityMiddleware(MiddlewareMixin):
    """
    Middleware to ensure API compatibility with existing Node.js frontend
    
    This middleware:
    1. Handles URL path compatibility
    2. Processes request/response format compatibility
    3. Maintains authentication token format
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """
        Process incoming requests for compatibility
        """
        # Handle URL path compatibility if needed
        # Most URLs should already match, but this provides a fallback
        
        # Handle specific Node.js style parameters
        if request.method == 'GET' and request.path.startswith('/api/'):
            # Convert Node.js style query parameters if needed
            query_params = request.GET.copy()
            
            # Handle pagination parameters
            if 'pageIndex' in query_params:
                # Node.js uses pageIndex, Django typically uses page
                page_index = query_params.get('pageIndex', '1')
                try:
                    # Convert to 1-based page number for Django
                    page = int(page_index) + 1 if int(page_index) > 0 else 1
                    query_params['page'] = str(page)
                except (ValueError, TypeError):
                    query_params['page'] = '1'
            
            # Handle pageSize parameter
            if 'pageSize' in query_params:
                page_size = query_params.get('pageSize', '20')
                query_params['page_size'] = page_size
            
            # Update request.GET with modified parameters
            request.GET = query_params
        
        return None
    
    def process_response(self, request, response):
        """
        Process outgoing responses for compatibility
        """
        # Only process JSON API responses
        if (hasattr(response, 'content_type') and 
            response.content_type and 
            'application/json' in response.content_type and
            request.path.startswith('/api/')):
            
            try:
                # Parse the response content
                if hasattr(response, 'data'):
                    # DRF Response object
                    data = response.data
                else:
                    # Regular Django JsonResponse
                    data = json.loads(response.content.decode('utf-8'))
                
                # Check if response is already in Node.js format
                if isinstance(data, dict) and 'code' in data and 'msg' in data:
                    # Already in correct format
                    return response
                
                # Convert to Node.js format
                if response.status_code >= 400:
                    # Error response
                    error_data = {
                        'code': self._get_error_code(response.status_code),
                        'msg': self._get_error_message(data, response.status_code),
                        'data': None
                    }
                    response.content = json.dumps(error_data, ensure_ascii=False).encode('utf-8')
                else:
                    # Success response
                    success_data = {
                        'code': 200,
                        'msg': 'ok',
                        'data': data
                    }
                    response.content = json.dumps(success_data, ensure_ascii=False).encode('utf-8')
                
            except (json.JSONDecodeError, AttributeError, TypeError) as e:
                logger.warning(f"Failed to process response for compatibility: {e}")
                # Return original response if processing fails
                pass
        
        return response
    
    def _get_error_code(self, status_code):
        """
        Convert HTTP status codes to Node.js style error codes
        """
        error_code_mapping = {
            400: 40001,  # Bad Request
            401: 40101,  # Unauthorized
            403: 40301,  # Forbidden
            404: 40401,  # Not Found
            422: 42201,  # Unprocessable Entity
            429: 42901,  # Rate Limited
            500: 50001,  # Internal Server Error
        }
        return error_code_mapping.get(status_code, status_code * 100 + 1)
    
    def _get_error_message(self, data, status_code):
        """
        Extract error message from response data (sanitized for security)
        """
        if isinstance(data, dict):
            # Try common error message fields
            for field in ['detail', 'message', 'error', 'msg']:
                if field in data:
                    message = data[field]
                    if isinstance(message, list) and message:
                        return self._sanitize_error_message(str(message[0]))
                    return self._sanitize_error_message(str(message))
            
            # Try field-specific errors
            for key, value in data.items():
                if isinstance(value, list) and value:
                    return self._sanitize_error_message(f"{key}: {value[0]}")
                elif isinstance(value, str):
                    return self._sanitize_error_message(f"{key}: {value}")
        
        # Default error messages (safe)
        default_messages = {
            400: '请求参数错误',
            401: '未授权访问',
            403: '权限不足',
            404: '资源不存在',
            422: '数据验证失败',
            429: '请求过于频繁',
            500: '服务器内部错误',
        }
        return default_messages.get(status_code, '请求失败')
    
    def _sanitize_error_message(self, message):
        """
        Sanitize error messages to prevent information leakage
        """
        # Remove potentially sensitive information
        sensitive_patterns = [
            'password',
            'token',
            'secret',
            'key',
            'database',
            'sql',
            'traceback',
            'exception',
            'error at',
            'file "',
            'line ',
        ]
        
        message_lower = message.lower()
        for pattern in sensitive_patterns:
            if pattern in message_lower:
                return '请求处理失败'  # Generic safe message
        
        # Limit message length to prevent verbose error exposure
        if len(message) > 100:
            return '请求处理失败'
        
        return message


class NodeJSCompatibilityRenderer(JSONRenderer):
    """
    Custom JSON renderer that ensures Node.js compatibility
    """
    
    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Render data in Node.js compatible format
        """
        if renderer_context and renderer_context.get('response'):
            response = renderer_context['response']
            
            # Check if data is already in Node.js format
            if isinstance(data, dict) and 'code' in data and 'msg' in data:
                return super().render(data, accepted_media_type, renderer_context)
            
            if response.status_code >= 400:
                # Error response
                error_message = self._extract_error_message(data)
                wrapped_data = {
                    'code': self._get_error_code(response.status_code),
                    'msg': error_message,
                    'data': None
                }
            else:
                # Success response
                wrapped_data = {
                    'code': 200,
                    'msg': 'ok',
                    'data': data
                }
            
            return super().render(wrapped_data, accepted_media_type, renderer_context)
        
        return super().render(data, accepted_media_type, renderer_context)
    
    def _get_error_code(self, status_code):
        """Convert HTTP status codes to Node.js style error codes"""
        error_code_mapping = {
            400: 40001,
            401: 40101,
            403: 40301,
            404: 40401,
            422: 42201,
            429: 42901,
            500: 50001,
        }
        return error_code_mapping.get(status_code, status_code * 100 + 1)
    
    def _extract_error_message(self, data):
        """Extract meaningful error message from DRF error data (sanitized)"""
        if isinstance(data, dict):
            # Handle DRF validation errors
            if 'detail' in data:
                return self._sanitize_error_message(str(data['detail']))
            
            # Handle field-specific errors
            for field, errors in data.items():
                if isinstance(errors, list) and errors:
                    return self._sanitize_error_message(f"{field}: {errors[0]}")
                elif isinstance(errors, str):
                    return self._sanitize_error_message(f"{field}: {errors}")
        
        elif isinstance(data, list) and data:
            return self._sanitize_error_message(str(data[0]))
        
        return '请求失败'
    
    def _sanitize_error_message(self, message):
        """Sanitize error messages to prevent information leakage"""
        # Same sanitization logic as in NodeJSCompatibilityMiddleware
        sensitive_patterns = [
            'password', 'token', 'secret', 'key', 'database', 'sql',
            'traceback', 'exception', 'error at', 'file "', 'line ',
        ]
        
        message_lower = message.lower()
        for pattern in sensitive_patterns:
            if pattern in message_lower:
                return '请求处理失败'
        
        if len(message) > 100:
            return '请求处理失败'
        
        return message


class WeChatAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware to handle WeChat-specific authentication compatibility
    """
    
    def process_request(self, request):
        """
        Process WeChat authentication headers and parameters
        """
        # Handle WeChat mini-program specific headers
        if request.path.startswith('/api/'):
            # Add WeChat-specific request processing if needed
            pass
        
        return None


class CORSCompatibilityMiddleware(MiddlewareMixin):
    """
    CORS middleware for frontend compatibility
    """
    
    def process_response(self, request, response):
        """
        Add CORS headers for frontend compatibility
        """
        if request.path.startswith('/api/'):
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response['Access-Control-Max-Age'] = '86400'
        
        return response
    
    def process_request(self, request):
        """
        Handle preflight OPTIONS requests
        """
        if request.method == 'OPTIONS' and request.path.startswith('/api/'):
            response = JsonResponse({})
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response['Access-Control-Max-Age'] = '86400'
            return response
        
        return None