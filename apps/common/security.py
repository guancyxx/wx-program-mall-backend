from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.contrib.admin.models import LogEntry
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseForbidden
from datetime import timedelta
import logging
import json

# Set up security logger
security_logger = logging.getLogger('security')


class SecurityMonitor:
    """Security monitoring and threat detection"""
    
    @staticmethod
    def log_security_event(event_type, user=None, ip_address=None, details=None):
        """Log security events"""
        from .models import AdminAuditLog
        
        try:
            AdminAuditLog.objects.create(
                user=user,
                action=event_type,
                message=details or f"Security event: {event_type}",
                ip_address=ip_address,
            )
        except Exception as e:
            security_logger.error(f"Failed to log security event: {e}")
    
    @staticmethod
    def check_suspicious_activity(user, ip_address):
        """Check for suspicious user activity"""
        if not user or not ip_address:
            return False
        
        # Check for multiple failed login attempts
        cache_key = f"failed_logins:{ip_address}"
        failed_attempts = cache.get(cache_key, 0)
        
        if failed_attempts >= 5:
            SecurityMonitor.log_security_event(
                'SUSPICIOUS_ACTIVITY',
                user=user,
                ip_address=ip_address,
                details=f"Multiple failed login attempts from IP: {ip_address}"
            )
            return True
        
        # Check for rapid successive logins
        cache_key = f"rapid_logins:{user.id}"
        recent_logins = cache.get(cache_key, 0)
        
        if recent_logins >= 10:  # More than 10 logins in the cache period
            SecurityMonitor.log_security_event(
                'SUSPICIOUS_ACTIVITY',
                user=user,
                ip_address=ip_address,
                details=f"Rapid successive logins for user: {user.username}"
            )
            return True
        
        return False
    
    @staticmethod
    def track_admin_actions(user, action, model_name, object_repr):
        """Track administrative actions for security monitoring"""
        sensitive_actions = ['DELETE', 'CHANGE']
        sensitive_models = ['User', 'Order', 'PaymentTransaction', 'MembershipStatus']
        
        if action in sensitive_actions and model_name in sensitive_models:
            SecurityMonitor.log_security_event(
                'ADMIN_ACTION',
                user=user,
                details=f"Admin {action} on {model_name}: {object_repr}"
            )
    
    @staticmethod
    def detect_privilege_escalation(user, requested_action):
        """Detect potential privilege escalation attempts"""
        if not user.is_staff and requested_action in ['admin_access', 'user_management']:
            SecurityMonitor.log_security_event(
                'PRIVILEGE_ESCALATION',
                user=user,
                details=f"Non-staff user attempted: {requested_action}"
            )
            return True
        
        if not user.is_superuser and requested_action in ['user_deletion', 'system_config']:
            SecurityMonitor.log_security_event(
                'PRIVILEGE_ESCALATION',
                user=user,
                details=f"Non-superuser attempted: {requested_action}"
            )
            return True
        
        return False


class RateLimitMiddleware:
    """Rate limiting middleware for API endpoints"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check rate limits before processing request
        if self.is_rate_limited(request):
            SecurityMonitor.log_security_event(
                'RATE_LIMIT_EXCEEDED',
                user=getattr(request, 'user', None),
                ip_address=self.get_client_ip(request),
                details=f"Rate limit exceeded for {request.path}"
            )
            return HttpResponseForbidden("Rate limit exceeded")
        
        response = self.get_response(request)
        return response
    
    def is_rate_limited(self, request):
        """Check if request should be rate limited"""
        ip_address = self.get_client_ip(request)
        
        # Different limits for different endpoints
        if request.path.startswith('/admin/'):
            limit = 100  # 100 requests per minute for admin
            window = 60
        elif request.path.startswith('/api/'):
            limit = 1000  # 1000 requests per minute for API
            window = 60
        else:
            return False  # No rate limiting for other paths
        
        cache_key = f"rate_limit:{ip_address}:{request.path}"
        current_requests = cache.get(cache_key, 0)
        
        if current_requests >= limit:
            return True
        
        # Increment counter
        cache.set(cache_key, current_requests + 1, window)
        return False
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityAuditLogger:
    """Comprehensive security audit logging"""
    
    @staticmethod
    def log_authentication_event(event_type, user=None, ip_address=None, user_agent=None, success=True):
        """Log authentication events"""
        details = {
            'event_type': event_type,
            'success': success,
            'user_agent': user_agent,
            'timestamp': timezone.now().isoformat(),
        }
        
        security_logger.info(
            f"Authentication event: {event_type}",
            extra={
                'user': user.username if user else 'anonymous',
                'ip_address': ip_address,
                'details': json.dumps(details),
            }
        )
        
        # Also store in database
        SecurityMonitor.log_security_event(
            event_type,
            user=user,
            ip_address=ip_address,
            details=json.dumps(details)
        )
    
    @staticmethod
    def log_data_access(user, model_name, action, object_id=None, sensitive=False):
        """Log data access events"""
        details = {
            'model': model_name,
            'action': action,
            'object_id': object_id,
            'sensitive': sensitive,
            'timestamp': timezone.now().isoformat(),
        }
        
        log_level = logging.WARNING if sensitive else logging.INFO
        security_logger.log(
            log_level,
            f"Data access: {action} on {model_name}",
            extra={
                'user': user.username if user else 'anonymous',
                'details': json.dumps(details),
            }
        )
    
    @staticmethod
    def log_system_event(event_type, details=None, severity='INFO'):
        """Log system-level security events"""
        log_data = {
            'event_type': event_type,
            'details': details,
            'timestamp': timezone.now().isoformat(),
        }
        
        log_level = getattr(logging, severity.upper(), logging.INFO)
        security_logger.log(
            log_level,
            f"System event: {event_type}",
            extra={'details': json.dumps(log_data)}
        )


# Signal handlers for authentication events
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log successful user login"""
    ip_address = RateLimitMiddleware(None).get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    SecurityAuditLogger.log_authentication_event(
        'LOGIN',
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        success=True
    )
    
    # Track login frequency for suspicious activity detection
    cache_key = f"rapid_logins:{user.id}"
    current_count = cache.get(cache_key, 0)
    cache.set(cache_key, current_count + 1, 300)  # 5 minute window
    
    # Check for suspicious activity
    SecurityMonitor.check_suspicious_activity(user, ip_address)


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log user logout"""
    if user:
        ip_address = RateLimitMiddleware(None).get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        SecurityAuditLogger.log_authentication_event(
            'LOGOUT',
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )


@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    """Log failed login attempts"""
    ip_address = RateLimitMiddleware(None).get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    username = credentials.get('username', 'unknown')
    
    SecurityAuditLogger.log_authentication_event(
        'LOGIN_FAILED',
        ip_address=ip_address,
        user_agent=user_agent,
        success=False
    )
    
    # Track failed attempts for rate limiting
    cache_key = f"failed_logins:{ip_address}"
    current_failures = cache.get(cache_key, 0)
    cache.set(cache_key, current_failures + 1, 900)  # 15 minute window
    
    # Log potential brute force attempt
    if current_failures >= 3:
        SecurityMonitor.log_security_event(
            'BRUTE_FORCE_ATTEMPT',
            ip_address=ip_address,
            details=f"Multiple failed login attempts for username: {username}"
        )


class SecurityReportGenerator:
    """Generate security reports and alerts"""
    
    @staticmethod
    def get_security_summary(days=7):
        """Get security summary for the last N days"""
        from .models import AdminAuditLog
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        logs = AdminAuditLog.objects.filter(
            created_at__range=[start_date, end_date]
        )
        
        summary = {
            'total_events': logs.count(),
            'login_events': logs.filter(action='LOGIN').count(),
            'failed_logins': logs.filter(action='LOGIN_FAILED').count(),
            'admin_actions': logs.filter(action='ADMIN_ACTION').count(),
            'suspicious_activities': logs.filter(action='SUSPICIOUS_ACTIVITY').count(),
            'privilege_escalations': logs.filter(action='PRIVILEGE_ESCALATION').count(),
            'rate_limit_violations': logs.filter(action='RATE_LIMIT_EXCEEDED').count(),
        }
        
        # Calculate security score (0-100)
        total_negative_events = (
            summary['failed_logins'] + 
            summary['suspicious_activities'] + 
            summary['privilege_escalations'] + 
            summary['rate_limit_violations']
        )
        
        if summary['total_events'] > 0:
            security_score = max(0, 100 - (total_negative_events / summary['total_events'] * 100))
        else:
            security_score = 100
        
        summary['security_score'] = round(security_score, 1)
        summary['period_start'] = start_date
        summary['period_end'] = end_date
        
        return summary
    
    @staticmethod
    def get_top_security_risks():
        """Identify top security risks"""
        from .models import AdminAuditLog
        
        # Get recent suspicious activities
        recent_risks = AdminAuditLog.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7),
            action__in=['SUSPICIOUS_ACTIVITY', 'PRIVILEGE_ESCALATION', 'BRUTE_FORCE_ATTEMPT']
        ).order_by('-created_at')[:10]
        
        risks = []
        for log in recent_risks:
            risk_level = 'HIGH' if log.action == 'PRIVILEGE_ESCALATION' else 'MEDIUM'
            risks.append({
                'timestamp': log.created_at,
                'type': log.action,
                'user': log.user.username if log.user else 'Anonymous',
                'ip_address': log.ip_address,
                'details': log.message,
                'risk_level': risk_level,
            })
        
        return risks
    
    @staticmethod
    def generate_security_alert(alert_type, details):
        """Generate security alert notification"""
        from .models import SystemNotification
        
        alert_messages = {
            'BRUTE_FORCE': 'Potential brute force attack detected',
            'PRIVILEGE_ESCALATION': 'Privilege escalation attempt detected',
            'SUSPICIOUS_ACTIVITY': 'Suspicious user activity detected',
            'SYSTEM_BREACH': 'Potential system breach detected',
        }
        
        message = alert_messages.get(alert_type, 'Security event detected')
        
        SystemNotification.create_system_notification(
            title=f"Security Alert: {alert_type}",
            message=f"{message}\n\nDetails: {details}",
            notification_type='error',
            priority='high'
        )
        
        # Also log to security logger
        SecurityAuditLogger.log_system_event(
            f"SECURITY_ALERT_{alert_type}",
            details=details,
            severity='WARNING'
        )