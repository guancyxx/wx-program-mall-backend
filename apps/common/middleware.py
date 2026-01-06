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
        if settings.DEBUG:
            return False

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