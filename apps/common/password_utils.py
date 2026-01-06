"""
Password hashing utilities with bcrypt compatibility and performance optimizations
"""

import bcrypt
import hashlib
import logging
import secrets
import re
import string
import traceback
import uuid
from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta
from django.contrib.auth.hashers import BasePasswordHasher, mask_hash
from django.utils.crypto import constant_time_compare
from django.core.exceptions import ValidationError

# Import performance optimization components
from .performance import (
    get_performance_monitor, get_password_validation_cache, 
    get_concurrent_hash_processor, get_db_connection_manager,
    performance_tracked
)

# Configure logging for security events
logger = logging.getLogger('security')


# ============================================================================
# COMPREHENSIVE ERROR HANDLING SYSTEM
# ============================================================================

class PasswordSecurityError(Exception):
    """
    Base exception class for password security system errors.
    
    This class provides the foundation for all password security related errors
    with comprehensive error handling, logging, and recovery mechanisms.
    
    Requirements addressed: 4.1, 4.2, 4.3, 4.4
    """
    
    def __init__(self, message: str, error_code: str = None, user_message: str = None,
                 admin_message: str = None, recovery_actions: List[str] = None,
                 requires_password_reset: bool = False, sensitive_data: Dict[str, Any] = None,
                 user_context: Dict[str, Any] = None):
        """
        Initialize password security error with comprehensive error information.
        
        Args:
            message: Technical error message for logging
            error_code: Unique error code for identification
            user_message: User-friendly error message (no sensitive data)
            admin_message: Detailed message for administrators
            recovery_actions: List of recommended recovery actions
            requires_password_reset: Whether error requires password reset
            sensitive_data: Sensitive data that should not be exposed to users
            user_context: User context for logging and recovery
        """
        super().__init__(message)
        
        self.error_code = error_code or 'PASSWORD_SECURITY_ERROR'
        self.user_message = user_message or 'A security error occurred. Please try again.'
        self.admin_message = admin_message or message
        self.recovery_actions = recovery_actions or []
        self.requires_password_reset = requires_password_reset
        self.sensitive_data = sensitive_data or {}
        self.user_context = user_context or {}
        self.timestamp = datetime.now()
        self.error_id = str(uuid.uuid4())
        
        # Ensure no sensitive data leaks into user message
        self._sanitize_user_message()
        
        # Log the error immediately
        self._log_error()
    
    def _sanitize_user_message(self):
        """
        Ensure user message contains no sensitive information.
        
        Requirements: 4.4 - Never expose internal hash details or salt information
        """
        # List of sensitive terms that should not appear in user messages
        sensitive_terms = [
            'salt', 'hash', 'bcrypt', 'md5', 'sha1', 'sha256', 'password_hash',
            'stack trace', 'traceback', 'exception', 'database', 'sql', 'query',
            'internal', 'system', 'debug', 'error_id', 'user_id'
        ]
        
        # Check if user message contains sensitive terms
        user_msg_lower = self.user_message.lower()
        for term in sensitive_terms:
            if term in user_msg_lower:
                # Replace with generic message
                self.user_message = 'A security error occurred. Please contact support if this issue persists.'
                break
    
    def _log_error(self):
        """
        Log error with appropriate level and context.
        
        Requirements: 4.2 - Log detailed technical errors for administrator review
        """
        try:
            # Create log context without sensitive data
            log_context = {
                'error_id': self.error_id,
                'error_code': self.error_code,
                'timestamp': self.timestamp.isoformat(),
                'user_context': self._sanitize_context(self.user_context),
                'recovery_actions': self.recovery_actions,
                'requires_password_reset': self.requires_password_reset
            }
            
            # Log with appropriate level based on error severity
            if self.requires_password_reset or 'CRITICAL' in self.error_code:
                logger.critical(f"Critical password security error: {self.admin_message}", 
                              extra=log_context, exc_info=True)
            elif 'CORRUPTION' in self.error_code or 'HASH' in self.error_code:
                logger.error(f"Password security error: {self.admin_message}", 
                           extra=log_context, exc_info=True)
            else:
                logger.warning(f"Password security warning: {self.admin_message}", 
                             extra=log_context)
                
        except Exception as e:
            # Fallback logging if structured logging fails
            logger.error(f"Failed to log password security error: {str(e)}")
    
    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove sensitive data from context for logging.
        
        Args:
            context: Original context dictionary
            
        Returns:
            Dict[str, Any]: Sanitized context safe for logging
        """
        if not context:
            return {}
        
        # Fields that are safe to log
        safe_fields = [
            'user_id', 'username', 'ip_address', 'user_agent', 'session_id',
            'request_path', 'auth_method', 'timestamp', 'operation', 'hash_type'
        ]
        
        sanitized = {}
        for key, value in context.items():
            if key in safe_fields:
                sanitized[key] = value
            elif 'password' not in key.lower() and 'hash' not in key.lower():
                # Include non-sensitive fields
                sanitized[key] = str(value)[:100]  # Limit length
        
        return sanitized
    
    def to_user_response(self) -> Dict[str, Any]:
        """
        Generate user-safe error response.
        
        Returns:
            Dict[str, Any]: Error response safe for user consumption
            
        Requirements: 4.1 - Provide user-friendly error messages
        """
        return {
            'success': False,
            'error_code': self.error_code,
            'message': self.user_message,
            'requires_password_reset': self.requires_password_reset,
            'timestamp': self.timestamp.isoformat(),
            'error_id': self.error_id,
            'support_message': 'If this issue persists, please contact support with error ID: ' + self.error_id
        }
    
    def to_admin_response(self) -> Dict[str, Any]:
        """
        Generate detailed admin error response.
        
        Returns:
            Dict[str, Any]: Detailed error response for administrators
            
        Requirements: 4.2 - Administrative error logging with technical details
        """
        return {
            'success': False,
            'error_id': self.error_id,
            'error_code': self.error_code,
            'user_message': self.user_message,
            'admin_message': self.admin_message,
            'technical_message': str(self),
            'recovery_actions': self.recovery_actions,
            'requires_password_reset': self.requires_password_reset,
            'user_context': self._sanitize_context(self.user_context),
            'sensitive_data_present': bool(self.sensitive_data),
            'timestamp': self.timestamp.isoformat(),
            'stack_trace': traceback.format_exc() if hasattr(self, '__traceback__') else None
        }


class HashCorruptionError(PasswordSecurityError):
    """
    Error raised when password hash corruption is detected.
    
    This error indicates that a password hash is corrupted or invalid,
    requiring immediate password reset for security.
    
    Requirements: 1.3, 1.5 - Salt corruption recovery and error handling
    """
    
    def __init__(self, hash_sample: str = None, corruption_type: str = None, 
                 user_context: Dict[str, Any] = None):
        """
        Initialize hash corruption error.
        
        Args:
            hash_sample: Safe sample of corrupted hash (first 8 chars)
            corruption_type: Type of corruption detected
            user_context: User context for logging
        """
        corruption_type = corruption_type or 'unknown'
        hash_sample = hash_sample[:8] + '...' if hash_sample and len(hash_sample) > 8 else 'unknown'
        
        super().__init__(
            message=f"Password hash corruption detected: {corruption_type} (sample: {hash_sample})",
            error_code='HASH_CORRUPTION',
            user_message='Your account requires a security update. Please reset your password to continue.',
            admin_message=f"Hash corruption detected - Type: {corruption_type}, Sample: {hash_sample}",
            recovery_actions=[
                'Initiate immediate password reset process',
                'Generate new secure hash upon reset completion',
                'Investigate potential data corruption causes',
                'Review backup and recovery procedures'
            ],
            requires_password_reset=True,
            sensitive_data={'hash_sample': hash_sample, 'corruption_type': corruption_type},
            user_context=user_context
        )


class LegacyPasswordError(PasswordSecurityError):
    """
    Error raised during legacy password operations.
    
    This error handles issues with legacy password verification and migration,
    providing appropriate recovery mechanisms.
    
    Requirements: 3.4 - Legacy verification failure handling
    """
    
    def __init__(self, legacy_type: str = None, operation: str = None, 
                 user_context: Dict[str, Any] = None):
        """
        Initialize legacy password error.
        
        Args:
            legacy_type: Type of legacy hash (md5, sha1, sha256)
            operation: Operation that failed (verification, migration)
            user_context: User context for logging
        """
        legacy_type = legacy_type or 'unknown'
        operation = operation or 'unknown'
        
        super().__init__(
            message=f"Legacy password {operation} failed for type: {legacy_type}",
            error_code='LEGACY_PASSWORD_ERROR',
            user_message='Your account needs a security update. Please reset your password.',
            admin_message=f"Legacy password {operation} failed - Type: {legacy_type}",
            recovery_actions=[
                'Initiate secure password reset process',
                'Disable legacy password verification for this user',
                'Log migration failure for audit trail',
                'Consider manual account recovery if needed'
            ],
            requires_password_reset=True,
            sensitive_data={'legacy_type': legacy_type, 'operation': operation},
            user_context=user_context
        )


class ValidationError(PasswordSecurityError):
    """
    Error raised when password validation fails.
    
    This error provides specific feedback about password strength requirements
    and suggestions for improvement.
    
    Requirements: 2.4 - Password validation with specific improvement suggestions
    """
    
    def __init__(self, validation_errors: List[str] = None, suggestions: List[str] = None,
                 strength_score: int = 0, user_context: Dict[str, Any] = None):
        """
        Initialize validation error.
        
        Args:
            validation_errors: List of specific validation failures
            suggestions: List of improvement suggestions
            strength_score: Password strength score (0-100)
            user_context: User context for logging
        """
        validation_errors = validation_errors or ['Password validation failed']
        suggestions = suggestions or ['Please choose a stronger password']
        
        # Create user-friendly message
        user_message = 'Password does not meet security requirements. ' + '; '.join(suggestions[:3])
        
        super().__init__(
            message=f"Password validation failed: {'; '.join(validation_errors)}",
            error_code='VALIDATION_FAILED',
            user_message=user_message,
            admin_message=f"Password validation failed - Errors: {len(validation_errors)}, Score: {strength_score}",
            recovery_actions=[
                'Display password requirements to user',
                'Provide specific improvement suggestions',
                'Allow user to try again with new password',
                'Consider password strength meter for user guidance'
            ],
            requires_password_reset=False,
            sensitive_data={
                'validation_errors': validation_errors,
                'suggestions': suggestions,
                'strength_score': strength_score
            },
            user_context=user_context
        )
        
        # Add validation-specific fields
        self.validation_errors = validation_errors
        self.suggestions = suggestions
        self.strength_score = strength_score
    
    def to_user_response(self) -> Dict[str, Any]:
        """
        Generate user response with validation details.
        
        Returns:
            Dict[str, Any]: User response with validation feedback
        """
        response = super().to_user_response()
        response.update({
            'validation_errors': self.validation_errors,
            'suggestions': self.suggestions,
            'strength_score': self.strength_score,
            'requirements': [
                'At least 8 characters long',
                'Contains uppercase and lowercase letters',
                'Contains numbers and special characters',
                'Not a common or easily guessable password'
            ]
        })
        return response


class AuthenticationError(PasswordSecurityError):
    """
    Error raised during authentication failures.
    
    This error handles various authentication failure scenarios with
    appropriate security monitoring and brute force detection.
    
    Requirements: 4.1, 4.3 - Authentication error handling and recovery
    """
    
    def __init__(self, failure_reason: str = None, attempt_count: int = 1,
                 is_brute_force: bool = False, user_context: Dict[str, Any] = None):
        """
        Initialize authentication error.
        
        Args:
            failure_reason: Specific reason for authentication failure
            attempt_count: Number of recent failed attempts
            is_brute_force: Whether this appears to be a brute force attempt
            user_context: User context for logging
        """
        failure_reason = failure_reason or 'Authentication failed'
        
        # Determine if account lockout is needed
        requires_lockout = attempt_count >= 5 or is_brute_force
        
        # Create appropriate user message
        if is_brute_force:
            user_message = 'Multiple failed login attempts detected. Your account has been temporarily locked for security.'
        elif requires_lockout:
            user_message = 'Too many failed login attempts. Please try again later or reset your password.'
        else:
            user_message = 'Login failed. Please check your credentials and try again.'
        
        super().__init__(
            message=f"Authentication failed: {failure_reason} (attempt {attempt_count})",
            error_code='AUTHENTICATION_FAILED',
            user_message=user_message,
            admin_message=f"Authentication failure - Reason: {failure_reason}, Attempts: {attempt_count}, Brute force: {is_brute_force}",
            recovery_actions=[
                'Monitor for additional failed attempts',
                'Consider account lockout if pattern continues',
                'Log security event for audit trail',
                'Provide password reset option if needed'
            ],
            requires_password_reset=requires_lockout,
            sensitive_data={
                'failure_reason': failure_reason,
                'attempt_count': attempt_count,
                'is_brute_force': is_brute_force
            },
            user_context=user_context
        )
        
        # Add authentication-specific fields
        self.failure_reason = failure_reason
        self.attempt_count = attempt_count
        self.is_brute_force = is_brute_force


class SystemError(PasswordSecurityError):
    """
    Error raised for system-level password security issues.
    
    This error handles unexpected system errors while ensuring
    no sensitive information is exposed to users.
    
    Requirements: 4.4 - No sensitive information exposure
    """
    
    def __init__(self, system_error: Exception = None, operation: str = None,
                 user_context: Dict[str, Any] = None):
        """
        Initialize system error.
        
        Args:
            system_error: Original system exception
            operation: Operation that was being performed
            user_context: User context for logging
        """
        operation = operation or 'unknown operation'
        error_type = type(system_error).__name__ if system_error else 'SystemError'
        error_message = str(system_error) if system_error else 'Unknown system error'
        
        super().__init__(
            message=f"System error during {operation}: {error_type} - {error_message}",
            error_code='SYSTEM_ERROR',
            user_message='A system error occurred. Please try again or contact support.',
            admin_message=f"System error during {operation}: {error_type} - {error_message}",
            recovery_actions=[
                'Check system logs for detailed error information',
                'Verify system configuration and dependencies',
                'Consider system health check and monitoring',
                'Escalate to system administrators if persistent'
            ],
            requires_password_reset=False,
            sensitive_data={
                'system_error_type': error_type,
                'system_error_message': error_message,
                'operation': operation
            },
            user_context=user_context
        )


class ErrorHandler:
    """
    Centralized error handler for password security operations.
    
    This class provides comprehensive error handling with recovery mechanisms,
    user-friendly messages, and administrative logging while ensuring no
    sensitive information is exposed to users.
    
    Requirements addressed: 4.1, 4.2, 4.3, 4.4
    """
    
    def __init__(self):
        """Initialize error handler."""
        self.logger = logging.getLogger('security.error_handler')
        self.security_monitor = None  # Will be set when SecurityMonitor is available
        
    def set_security_monitor(self, security_monitor):
        """
        Set security monitor for error logging.
        
        Args:
            security_monitor: SecurityMonitor instance
        """
        self.security_monitor = security_monitor
    
    def handle_hash_corruption(self, error: Exception, hash_sample: str = None,
                             user_context: Dict[str, Any] = None) -> HashCorruptionError:
        """
        Handle password hash corruption errors.
        
        Args:
            error: Original exception
            hash_sample: Sample of corrupted hash
            user_context: User context for logging
            
        Returns:
            HashCorruptionError: Comprehensive error with recovery actions
            
        Requirements: 1.3 - Hash corruption recovery mechanisms
        """
        try:
            # Determine corruption type from error message
            error_msg = str(error).lower()
            if 'salt' in error_msg:
                corruption_type = 'salt_corruption'
            elif 'format' in error_msg:
                corruption_type = 'format_corruption'
            elif 'encoding' in error_msg:
                corruption_type = 'encoding_corruption'
            else:
                corruption_type = 'unknown_corruption'
            
            # Create hash corruption error
            hash_error = HashCorruptionError(
                hash_sample=hash_sample,
                corruption_type=corruption_type,
                user_context=user_context
            )
            
            # Log to security monitor if available
            if self.security_monitor:
                self.security_monitor.log_security_error(error, {
                    'operation': 'hash_corruption_handling',
                    'corruption_type': corruption_type,
                    'error_id': hash_error.error_id,
                    **(user_context or {})
                })
            
            return hash_error
            
        except Exception as e:
            self.logger.error(f"Error handling hash corruption: {str(e)}")
            return HashCorruptionError(user_context=user_context)
    
    def handle_legacy_password_error(self, error: Exception, legacy_type: str = None,
                                   operation: str = None, user_context: Dict[str, Any] = None) -> LegacyPasswordError:
        """
        Handle legacy password operation errors.
        
        Args:
            error: Original exception
            legacy_type: Type of legacy hash
            operation: Operation that failed
            user_context: User context for logging
            
        Returns:
            LegacyPasswordError: Comprehensive error with recovery actions
            
        Requirements: 3.4 - Legacy verification failure handling
        """
        try:
            # Create legacy password error
            legacy_error = LegacyPasswordError(
                legacy_type=legacy_type,
                operation=operation,
                user_context=user_context
            )
            
            # Log to security monitor if available
            if self.security_monitor:
                self.security_monitor.log_security_error(error, {
                    'operation': 'legacy_password_error_handling',
                    'legacy_type': legacy_type,
                    'failed_operation': operation,
                    'error_id': legacy_error.error_id,
                    **(user_context or {})
                })
            
            return legacy_error
            
        except Exception as e:
            self.logger.error(f"Error handling legacy password error: {str(e)}")
            return LegacyPasswordError(user_context=user_context)
    
    def handle_validation_error(self, validation_result, user_context: Dict[str, Any] = None) -> ValidationError:
        """
        Handle password validation errors.
        
        Args:
            validation_result: ValidationResult object with errors and suggestions
            user_context: User context for logging
            
        Returns:
            ValidationError: Comprehensive validation error
            
        Requirements: 2.4 - Specific improvement suggestions for weak passwords
        """
        try:
            # Create validation error
            validation_error = ValidationError(
                validation_errors=validation_result.errors,
                suggestions=validation_result.suggestions,
                strength_score=validation_result.strength_score,
                user_context=user_context
            )
            
            # Log to security monitor if available
            if self.security_monitor:
                self.security_monitor.log_authentication_attempt(
                    user=user_context.get('user_id', 'unknown') if user_context else 'unknown',
                    success=False,
                    details={
                        'operation': 'password_validation',
                        'error_id': validation_error.error_id,
                        'strength_score': validation_result.strength_score,
                        'error_count': len(validation_result.errors),
                        **(user_context or {})
                    }
                )
            
            return validation_error
            
        except Exception as e:
            self.logger.error(f"Error handling validation error: {str(e)}")
            return ValidationError(user_context=user_context)
    
    def handle_authentication_error(self, error: Exception, failure_reason: str = None,
                                  attempt_count: int = 1, user_context: Dict[str, Any] = None) -> AuthenticationError:
        """
        Handle authentication errors with brute force detection.
        
        Args:
            error: Original exception
            failure_reason: Specific reason for failure
            attempt_count: Number of recent failed attempts
            user_context: User context for logging
            
        Returns:
            AuthenticationError: Comprehensive authentication error
            
        Requirements: 4.1, 4.3 - Authentication error handling and recovery
        """
        try:
            # Detect potential brute force
            is_brute_force = attempt_count >= 5
            
            # Create authentication error
            auth_error = AuthenticationError(
                failure_reason=failure_reason or str(error),
                attempt_count=attempt_count,
                is_brute_force=is_brute_force,
                user_context=user_context
            )
            
            # Log to security monitor if available
            if self.security_monitor:
                self.security_monitor.log_authentication_attempt(
                    user=user_context.get('user_id', 'unknown') if user_context else 'unknown',
                    success=False,
                    details={
                        'operation': 'authentication_error_handling',
                        'failure_reason': failure_reason,
                        'attempt_count': attempt_count,
                        'is_brute_force': is_brute_force,
                        'error_id': auth_error.error_id,
                        **(user_context or {})
                    }
                )
            
            return auth_error
            
        except Exception as e:
            self.logger.error(f"Error handling authentication error: {str(e)}")
            return AuthenticationError(user_context=user_context)
    
    def handle_system_error(self, error: Exception, operation: str = None,
                          user_context: Dict[str, Any] = None) -> SystemError:
        """
        Handle system-level errors with secure information handling.
        
        Args:
            error: Original system exception
            operation: Operation that was being performed
            user_context: User context for logging
            
        Returns:
            SystemError: Comprehensive system error
            
        Requirements: 4.4 - No sensitive information exposure
        """
        try:
            # Create system error
            system_error = SystemError(
                system_error=error,
                operation=operation,
                user_context=user_context
            )
            
            # Log to security monitor if available
            if self.security_monitor:
                self.security_monitor.log_security_error(error, {
                    'operation': 'system_error_handling',
                    'failed_operation': operation,
                    'error_id': system_error.error_id,
                    **(user_context or {})
                })
            
            return system_error
            
        except Exception as e:
            self.logger.error(f"Error handling system error: {str(e)}")
            return SystemError(user_context=user_context)
    
    def create_recovery_response(self, error: PasswordSecurityError, 
                               for_admin: bool = False) -> Dict[str, Any]:
        """
        Create comprehensive recovery response for password security errors.
        
        Args:
            error: PasswordSecurityError instance
            for_admin: Whether to include admin details
            
        Returns:
            Dict[str, Any]: Recovery response with appropriate level of detail
            
        Requirements: 4.1, 4.2 - User-friendly and administrative error responses
        """
        try:
            if for_admin:
                response = error.to_admin_response()
            else:
                response = error.to_user_response()
            
            # Add recovery guidance
            if error.requires_password_reset:
                response['recovery_guidance'] = {
                    'immediate_action': 'Password reset required',
                    'steps': [
                        'Click "Forgot Password" or contact support',
                        'Check your email for reset instructions',
                        'Create a new strong password',
                        'Log in with your new password'
                    ],
                    'support_available': True
                }
            else:
                response['recovery_guidance'] = {
                    'immediate_action': 'Retry with corrections',
                    'steps': [
                        'Review the error message and suggestions',
                        'Make the recommended changes',
                        'Try again with the corrected information'
                    ],
                    'support_available': False
                }
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error creating recovery response: {str(e)}")
            return {
                'success': False,
                'error_code': 'RECOVERY_ERROR',
                'message': 'Unable to generate recovery response. Please contact support.',
                'error_id': str(uuid.uuid4()),
                'timestamp': datetime.now().isoformat()
            }


# Global error handler instance
_error_handler = None

def get_error_handler() -> ErrorHandler:
    """
    Get global error handler instance (singleton pattern).
    
    Returns:
        ErrorHandler: Global error handler instance
    """
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


class SecurePasswordHasher(BasePasswordHasher):
    """
    Secure password hasher using bcrypt with enhanced security features and performance optimizations.
    
    This hasher addresses the "Invalid salt" error by implementing:
    - Cryptographically secure salt generation
    - Proper error handling for salt corruption
    - Configurable bcrypt rounds (default 12)
    - Enhanced logging for security events
    - Comprehensive error handling and recovery mechanisms
    - Performance optimizations for concurrent access
    - Caching for improved performance
    
    Requirements addressed: 1.1, 1.3, 1.4, 1.5, 4.1, 4.2, 4.3, 4.4, 7.1, 7.2, 7.3, 7.4
    """
    algorithm = "secure_bcrypt"
    library = "bcrypt"
    
    def __init__(self, rounds=None):
        """Initialize with configurable rounds and performance optimizations."""
        self.rounds = rounds or 12
        if self.rounds < 4:
            raise ValueError("BCrypt rounds must be at least 4")
        if self.rounds > 31:
            raise ValueError("BCrypt rounds must be at most 31")
        
        # Initialize error handler
        self.error_handler = get_error_handler()
        
        # Initialize performance components
        self.performance_monitor = get_performance_monitor()
        self.hash_processor = get_concurrent_hash_processor()

    @performance_tracked('secure_password_hasher.encode')
    def encode(self, password, salt=None):
        """
        Encode password using bcrypt with secure salt generation, comprehensive error handling,
        and performance optimizations.
        
        Args:
            password (str): Plain text password to hash
            salt (bytes, optional): Salt bytes. If None, generates secure salt.
            
        Returns:
            str: Encoded password hash in format "algorithm$hash"
            
        Raises:
            HashCorruptionError: If password encoding fails due to corruption
            SystemError: If system-level error occurs
        """
        def _encode_operation():
            try:
                # Ensure password is bytes
                if isinstance(password, str):
                    password_bytes = password.encode('utf-8')
                elif not isinstance(password, bytes):
                    raise ValueError("Password must be string or bytes")
                else:
                    password_bytes = password
                
                # Generate secure salt if not provided
                if salt is None:
                    salt_bytes = self.generate_salt()
                elif isinstance(salt, str):
                    # Handle legacy salt strings by converting to bytes
                    try:
                        salt_bytes = salt.encode('ascii')
                    except UnicodeEncodeError:
                        logger.warning("Invalid salt encoding detected, generating new salt")
                        salt_bytes = self.generate_salt()
                elif not isinstance(salt, bytes):
                    logger.warning("Invalid salt type detected, generating new salt")
                    salt_bytes = self.generate_salt()
                else:
                    salt_bytes = salt
                
                # Validate salt format for bcrypt
                if not self._is_valid_bcrypt_salt(salt_bytes):
                    logger.warning("Invalid bcrypt salt format detected, generating new salt")
                    salt_bytes = self.generate_salt()
                
                # Hash the password
                hash_bytes = bcrypt.hashpw(password_bytes, salt_bytes)
                hash_str = hash_bytes.decode('ascii')
                
                # Log successful hash generation (without sensitive data)
                logger.debug(f"Password hash generated successfully with algorithm {self.algorithm}", 
                            extra={'user': 'unknown', 'ip_address': 'unknown'})
                
                # Return the hash in Django format (algorithm$hash)
                # Note: bcrypt hash already starts with $, so we don't add another $
                return f"{self.algorithm}{hash_str}"
                
            except Exception as e:
                # Handle error using comprehensive error handler
                if 'salt' in str(e).lower() or 'invalid' in str(e).lower():
                    # This is likely a hash corruption issue
                    hash_error = self.error_handler.handle_hash_corruption(
                        error=e,
                        hash_sample=str(salt_bytes)[:8] if salt_bytes else None,
                        user_context={'operation': 'password_encoding', 'algorithm': self.algorithm}
                    )
                    raise hash_error
                else:
                    # This is a system error
                    system_error = self.error_handler.handle_system_error(
                        error=e,
                        operation='password_encoding',
                        user_context={'algorithm': self.algorithm}
                    )
                    raise system_error
        
        # Use concurrent hash processor for optimized performance
        return self.hash_processor.process_hash_operation(_encode_operation)

    @performance_tracked('secure_password_hasher.verify')
    def verify(self, password, encoded):
        """
        Verify password against encoded hash with enhanced error handling and performance optimizations.
        
        Args:
            password (str): Plain text password to verify
            encoded (str): Encoded password hash
            
        Returns:
            bool: True if password matches hash, False otherwise
            
        Raises:
            HashCorruptionError: If hash corruption is detected
            SystemError: If system-level error occurs
        """
        def _verify_operation():
            try:
                # Parse the encoded hash - handle both old format ($$) and new format ($)
                if encoded.startswith(f"{self.algorithm}$$"):
                    # Old format with double $ - extract the bcrypt hash part
                    hash_str = encoded[len(f"{self.algorithm}$$"):]
                    hash_str = "$" + hash_str  # Add back the $ for bcrypt
                elif encoded.startswith(f"{self.algorithm}$"):
                    # New format with single $ - extract the bcrypt hash part
                    hash_str = encoded[len(f"{self.algorithm}"):]
                else:
                    # Try standard Django format parsing
                    algorithm, hash_str = encoded.split('$', 1)
                    if algorithm != self.algorithm:
                        logger.warning(f"Algorithm mismatch: expected {self.algorithm}, got {algorithm}")
                        return False
                
                # Ensure password is bytes
                if isinstance(password, str):
                    password_bytes = password.encode('utf-8')
                elif not isinstance(password, bytes):
                    return False
                else:
                    password_bytes = password
                
                # Ensure hash is bytes
                if isinstance(hash_str, str):
                    hash_bytes = hash_str.encode('ascii')
                else:
                    hash_bytes = hash_str
                
                # Verify the password
                result = bcrypt.checkpw(password_bytes, hash_bytes)
                
                # Log verification attempt (without sensitive data)
                if result:
                    logger.debug("Password verification successful")
                else:
                    logger.debug("Password verification failed")
                
                return result
                
            except ValueError as e:
                if "Invalid salt" in str(e) or "salt" in str(e).lower():
                    # Handle salt corruption with comprehensive error handling
                    hash_error = self.error_handler.handle_hash_corruption(
                        error=e,
                        hash_sample=encoded[:8] if encoded else None,
                        user_context={
                            'operation': 'password_verification',
                            'algorithm': self.algorithm,
                            'corruption_type': 'salt_corruption'
                        }
                    )
                    # For verification, we return False but log the corruption
                    logger.error(f"Hash corruption detected during verification: {hash_error.error_id}")
                    return False
                else:
                    # Other ValueError types
                    logger.error(f"Password verification error: {str(e)}")
                    return False
            except Exception as e:
                # Handle unexpected system errors
                system_error = self.error_handler.handle_system_error(
                    error=e,
                    operation='password_verification',
                    user_context={'algorithm': self.algorithm}
                )
                logger.error(f"System error during password verification: {system_error.error_id}")
                return False
        
        # Use concurrent hash processor for optimized performance
        return self.hash_processor.process_hash_operation(_verify_operation)

    def safe_summary(self, encoded):
        """
        Return a safe summary of the password hash for display.
        
        Args:
            encoded (str): Encoded password hash
            
        Returns:
            dict: Safe summary with masked hash
        """
        try:
            # Handle both old format ($$) and new format ($)
            if encoded.startswith(f"{self.algorithm}$$"):
                # Old format with double $
                hash_str = encoded[len(f"{self.algorithm}$$"):]
                hash_str = "$" + hash_str  # Add back the $ for bcrypt
                algorithm = self.algorithm
            elif encoded.startswith(f"{self.algorithm}$"):
                # New format with single $
                hash_str = encoded[len(f"{self.algorithm}"):]
                algorithm = self.algorithm
            else:
                # Try standard Django format parsing
                algorithm, hash_str = encoded.split('$', 1)
                if algorithm != self.algorithm:
                    return {'algorithm': algorithm, 'hash': '[invalid algorithm]'}
            
            return {
                'algorithm': algorithm,
                'hash': mask_hash(hash_str),
                'rounds': self._extract_rounds(hash_str),
            }
        except Exception as e:
            # Log error but return safe default
            logger.warning(f"Error creating safe summary: {str(e)}")
            return {'algorithm': 'unknown', 'hash': '[invalid hash]'}

    def must_update(self, encoded):
        """
        Check if password hash needs updating due to insufficient rounds.
        
        Args:
            encoded (str): Encoded password hash
            
        Returns:
            bool: True if hash should be updated
        """
        try:
            # Handle both old format ($$) and new format ($)
            if encoded.startswith(f"{self.algorithm}$$"):
                # Old format with double $ - needs update to new format
                return True
            elif encoded.startswith(f"{self.algorithm}$"):
                # New format with single $
                hash_str = encoded[len(f"{self.algorithm}"):]
                algorithm = self.algorithm
            else:
                # Try standard Django format parsing
                algorithm, hash_str = encoded.split('$', 1)
                if algorithm != self.algorithm:
                    return True
            
            # Extract rounds from bcrypt hash
            current_rounds = self._extract_rounds(hash_str)
            if current_rounds is None:
                return True
            
            # Update if current rounds are less than configured rounds
            return current_rounds < self.rounds
            
        except Exception as e:
            # If we can't parse the hash, it should be updated
            logger.warning(f"Error checking update requirement: {str(e)}")
            return True

    def harden_runtime(self, password, encoded):
        """
        Harden against timing attacks by ensuring consistent runtime.
        
        This method is called by Django to prevent timing attacks
        when password verification fails.
        """
        # Perform a dummy bcrypt operation to maintain consistent timing
        try:
            dummy_salt = self.generate_salt()
            if isinstance(password, str):
                password = password.encode('utf-8')
            bcrypt.hashpw(password, dummy_salt)
        except Exception:
            pass  # Ignore errors in dummy operation

    def generate_salt(self, rounds=None):
        """
        Generate cryptographically secure salt for bcrypt with enhanced error handling.
        
        Args:
            rounds (int, optional): Number of rounds. Uses instance default if None.
            
        Returns:
            bytes: Secure bcrypt salt
            
        Raises:
            SystemError: If salt generation fails
        """
        try:
            rounds = rounds or self.rounds
            if rounds < 4 or rounds > 31:
                raise ValueError(f"Invalid rounds: {rounds}. Must be between 4 and 31.")
            
            # Generate cryptographically secure salt
            salt = bcrypt.gensalt(rounds=rounds)
            
            # Validate the generated salt
            if not self._is_valid_bcrypt_salt(salt):
                raise ValueError("Generated salt failed validation")
            
            logger.debug(f"Secure salt generated with {rounds} rounds", 
                        extra={'user': 'unknown', 'ip_address': 'unknown'})
            return salt
            
        except Exception as e:
            # Handle salt generation errors
            system_error = self.error_handler.handle_system_error(
                error=e,
                operation='salt_generation',
                user_context={'rounds': rounds}
            )
            raise system_error

    def _is_valid_bcrypt_salt(self, salt):
        """
        Validate bcrypt salt format.
        
        Args:
            salt (bytes): Salt to validate
            
        Returns:
            bool: True if salt is valid bcrypt format
        """
        try:
            if not isinstance(salt, bytes):
                return False
            
            salt_str = salt.decode('ascii')
            
            # Bcrypt salt format: $2[abxy]$rounds$salt
            # Valid prefixes: $2a$, $2b$, $2x$, $2y$
            valid_prefixes = ['$2a$', '$2b$', '$2x$', '$2y$']
            
            if not any(salt_str.startswith(prefix) for prefix in valid_prefixes):
                return False
            
            # Check if we can extract rounds
            parts = salt_str.split('$')
            if len(parts) < 4:
                return False
            
            try:
                rounds = int(parts[2])
                if rounds < 4 or rounds > 31:
                    return False
            except ValueError:
                return False
            
            # Salt should be exactly 29 characters total for the salt portion
            # Format: $2a$12$22characters (29 total)
            if len(salt_str) != 29:
                return False
            
            return True
            
        except Exception:
            return False

    def _extract_rounds(self, hash_str):
        """
        Extract rounds from bcrypt hash string.
        
        Args:
            hash_str (str): Bcrypt hash string
            
        Returns:
            int or None: Number of rounds, or None if extraction fails
        """
        try:
            # Bcrypt hash format: $2[abxy]$rounds$salthash
            parts = hash_str.split('$')
            if len(parts) >= 3:
                return int(parts[2])
        except (ValueError, IndexError):
            pass
        return None


class BCryptPasswordHasher(BasePasswordHasher):
    """
    Secure password hasher using bcrypt with compatibility for Node.js bcrypt
    """
    algorithm = "bcrypt"
    rounds = 12  # Default rounds for security

    def encode(self, password, salt):
        """
        Encode password using bcrypt
        """
        if isinstance(password, str):
            password = password.encode('utf-8')
        
        # Generate salt if not provided
        if not salt:
            salt = bcrypt.gensalt(rounds=self.rounds)
        elif isinstance(salt, str):
            salt = salt.encode('utf-8')
        
        # Hash the password
        hash_bytes = bcrypt.hashpw(password, salt)
        hash_str = hash_bytes.decode('ascii')
        
        return f"{self.algorithm}${hash_str}"

    def verify(self, password, encoded):
        """
        Verify password against encoded hash
        """
        algorithm, hash_str = encoded.split('$', 1)
        assert algorithm == self.algorithm
        
        if isinstance(password, str):
            password = password.encode('utf-8')
        
        hash_bytes = hash_str.encode('ascii')
        
        return bcrypt.checkpw(password, hash_bytes)

    def safe_summary(self, encoded):
        """
        Return a summary of the password hash for display
        """
        algorithm, hash_str = encoded.split('$', 1)
        assert algorithm == self.algorithm
        return {
            'algorithm': algorithm,
            'hash': mask_hash(hash_str),
        }

    def harden_runtime(self, password, encoded):
        """
        Harden against timing attacks
        """
        pass

    def must_update(self, encoded):
        """
        Check if password hash needs updating
        """
        try:
            algorithm, hash_str = encoded.split('$', 1)
            # Check if rounds are sufficient
            if hash_str.startswith('$2b$'):
                rounds_str = hash_str.split('$')[2]
                rounds = int(rounds_str)
                return rounds < self.rounds
        except (ValueError, IndexError):
            return True
        return False


class NodeJSCompatiblePasswordHasher:
    """
    Password hasher compatible with Node.js bcrypt implementation
    """
    
    @staticmethod
    def hash_password(password, rounds=12):
        """
        Hash password using bcrypt (Node.js compatible)
        
        Args:
            password (str): Plain text password
            rounds (int): Number of salt rounds (default: 12)
            
        Returns:
            str: Bcrypt hash string
        """
        if isinstance(password, str):
            password = password.encode('utf-8')
        
        # Generate salt and hash
        salt = bcrypt.gensalt(rounds=rounds)
        hash_bytes = bcrypt.hashpw(password, salt)
        
        return hash_bytes.decode('ascii')
    
    @staticmethod
    def verify_password(password, hash_str):
        """
        Verify password against bcrypt hash
        
        Args:
            password (str): Plain text password
            hash_str (str): Bcrypt hash string
            
        Returns:
            bool: True if password matches hash
        """
        if isinstance(password, str):
            password = password.encode('utf-8')
        
        if isinstance(hash_str, str):
            hash_bytes = hash_str.encode('ascii')
        else:
            hash_bytes = hash_str
        
        try:
            return bcrypt.checkpw(password, hash_bytes)
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_bcrypt_hash(hash_str):
        """
        Check if string is a valid bcrypt hash
        
        Args:
            hash_str (str): Hash string to check
            
        Returns:
            bool: True if valid bcrypt hash
        """
        if not isinstance(hash_str, str):
            return False
        
        # Bcrypt hashes start with $2a$, $2b$, $2x$, or $2y$
        bcrypt_prefixes = ['$2a$', '$2b$', '$2x$', '$2y$']
        return any(hash_str.startswith(prefix) for prefix in bcrypt_prefixes)


class LegacyPasswordHandler:
    """
    Comprehensive legacy password migration system that safely handles and migrates
    legacy password hashes while providing audit trails and secure error handling.
    
    This handler supports:
    - MD5, SHA1, and SHA256 legacy hash verification
    - Automatic password migration during successful authentication
    - Migration logging and audit trail functionality
    - Secure reset process for legacy verification failures
    """
    
    # Supported legacy hash formats
    SUPPORTED_FORMATS = ['md5', 'sha1', 'sha256', 'plain']
    
    def __init__(self):
        """Initialize the legacy password handler."""
        self.migration_logger = logging.getLogger('security.migration')
        self.migration_logger.info("LegacyPasswordHandler initialized")
    
    def verify_legacy_hash(self, password: str, hash_str: str, hash_type: str = None) -> bool:
        """
        Verify password against legacy hash formats with enhanced error handling.
        
        Args:
            password (str): Plain text password to verify
            hash_str (str): Legacy hash string
            hash_type (str, optional): Type of legacy hash. If None, auto-detect.
            
        Returns:
            bool: True if password matches hash, False otherwise
        """
        try:
            if not password or not hash_str:
                self.migration_logger.warning("Empty password or hash provided for legacy verification")
                return False
            
            # Auto-detect hash type if not provided
            if hash_type is None:
                hash_type = self.detect_hash_type(hash_str)
                if hash_type is None:
                    self.migration_logger.warning(f"Could not detect hash type for hash: {hash_str[:8]}...")
                    return False
            
            # Normalize hash type
            hash_type = hash_type.lower()
            
            if hash_type not in self.SUPPORTED_FORMATS:
                self.migration_logger.error(f"Unsupported hash type: {hash_type}")
                return False
            
            # Verify based on hash type
            if hash_type == 'md5':
                computed_hash = hashlib.md5(password.encode('utf-8')).hexdigest()
            elif hash_type == 'sha1':
                computed_hash = hashlib.sha1(password.encode('utf-8')).hexdigest()
            elif hash_type == 'sha256':
                computed_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            elif hash_type == 'plain':
                # Handle plain text passwords (emergency migration only)
                self.migration_logger.warning("Plain text password verification attempted")
                return constant_time_compare(password, hash_str)
            else:
                return False
            
            # Use constant-time comparison to prevent timing attacks
            result = constant_time_compare(computed_hash.lower(), hash_str.lower())
            
            # Log verification attempt (without sensitive data)
            if result:
                self.migration_logger.info(f"Legacy password verification successful for hash type: {hash_type}")
            else:
                self.migration_logger.debug(f"Legacy password verification failed for hash type: {hash_type}")
            
            return result
            
        except Exception as e:
            self.migration_logger.error(f"Error during legacy password verification: {type(e).__name__}: {str(e)}")
            return False
    
    def detect_hash_type(self, hash_str: str) -> Optional[str]:
        """
        Detect the type of legacy hash based on its characteristics.
        
        Args:
            hash_str (str): Hash string to analyze
            
        Returns:
            Optional[str]: Detected hash type or None if unknown
        """
        if not hash_str or not isinstance(hash_str, str):
            return None
        
        # Remove any whitespace
        hash_str = hash_str.strip()
        
        # Check hash length and character patterns
        if len(hash_str) == 32 and all(c in '0123456789abcdefABCDEF' for c in hash_str):
            return 'md5'
        elif len(hash_str) == 40 and all(c in '0123456789abcdefABCDEF' for c in hash_str):
            return 'sha1'
        elif len(hash_str) == 64 and all(c in '0123456789abcdefABCDEF' for c in hash_str):
            return 'sha256'
        elif len(hash_str) < 32 and not all(c in '0123456789abcdefABCDEF' for c in hash_str):
            # Might be plain text (very insecure, but handle for emergency migration)
            return 'plain'
        
        return None
    
    def migrate_to_secure_hash(self, password: str, legacy_hash: str, user_context: Optional[Dict] = None) -> Optional[str]:
        """
        Migrate legacy password to secure bcrypt hash with comprehensive logging.
        
        Args:
            password (str): Plain text password
            legacy_hash (str): Legacy hash string
            user_context (dict, optional): User context for logging
            
        Returns:
            Optional[str]: New secure hash if migration successful, None otherwise
        """
        try:
            # Detect legacy hash type
            legacy_type = self.detect_hash_type(legacy_hash)
            if legacy_type is None:
                self.migration_logger.error("Cannot migrate: unknown legacy hash type")
                return None
            
            # Verify legacy password first
            if not self.verify_legacy_hash(password, legacy_hash, legacy_type):
                self.migration_logger.warning(f"Migration failed: legacy password verification failed for type {legacy_type}")
                return None
            
            # Create new secure hash using SecurePasswordHasher
            hasher = SecurePasswordHasher()
            new_hash = hasher.encode(password)
            
            # Log successful migration
            user_id = user_context.get('user_id', 'unknown') if user_context else 'unknown'
            ip_address = user_context.get('ip_address', 'unknown') if user_context else 'unknown'
            
            self.migration_logger.info(
                f"Password migration successful: user_id={user_id}, "
                f"from_type={legacy_type}, to_type=secure_bcrypt, ip={ip_address}",
                extra={
                    'user_id': user_id,
                    'ip_address': ip_address,
                    'migration_type': f"{legacy_type}_to_secure_bcrypt",
                    'timestamp': logging.Formatter().formatTime(logging.LogRecord(
                        name='', level=0, pathname='', lineno=0, msg='', args=(), exc_info=None
                    ))
                }
            )
            
            return new_hash
            
        except Exception as e:
            self.migration_logger.error(
                f"Password migration failed: {type(e).__name__}: {str(e)}",
                extra={'user_context': user_context}
            )
            return None
    
    def is_legacy_hash(self, hash_str: str) -> bool:
        """
        Check if a hash string is a legacy format that needs migration.
        
        Args:
            hash_str (str): Hash string to check
            
        Returns:
            bool: True if hash is a legacy format
        """
        if not hash_str or not isinstance(hash_str, str):
            return False
        
        # Check if it's already a secure bcrypt hash
        if hash_str.startswith('secure_bcrypt$') or hash_str.startswith('bcrypt$'):
            return False
        
        # Check if it matches any legacy format
        detected_type = self.detect_hash_type(hash_str)
        return detected_type is not None and detected_type in self.SUPPORTED_FORMATS
    
    def handle_legacy_verification_failure(self, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Handle legacy password verification failures with secure reset process.
        
        Args:
            user_context (dict, optional): User context for logging and processing
            
        Returns:
            Dict[str, Any]: Response with error handling instructions
        """
        try:
            user_id = user_context.get('user_id', 'unknown') if user_context else 'unknown'
            ip_address = user_context.get('ip_address', 'unknown') if user_context else 'unknown'
            
            # Log the verification failure
            self.migration_logger.warning(
                f"Legacy password verification failure: user_id={user_id}, ip={ip_address}",
                extra={
                    'user_id': user_id,
                    'ip_address': ip_address,
                    'event_type': 'legacy_verification_failure',
                    'requires_password_reset': True
                }
            )
            
            return {
                'success': False,
                'error_code': 'LEGACY_VERIFICATION_FAILED',
                'message': 'Authentication failed. Please reset your password to continue.',
                'requires_password_reset': True,
                'user_message': 'Your account requires a password reset for security reasons. Please check your email for reset instructions.',
                'admin_message': f'Legacy password verification failed for user {user_id}. Password reset required.',
                'next_steps': [
                    'Initiate secure password reset process',
                    'Send password reset email to user',
                    'Log security event for audit trail'
                ]
            }
            
        except Exception as e:
            self.migration_logger.error(f"Error handling legacy verification failure: {str(e)}")
            return {
                'success': False,
                'error_code': 'SYSTEM_ERROR',
                'message': 'System error occurred. Please contact support.',
                'requires_password_reset': True,
                'user_message': 'A system error occurred. Please contact support for assistance.',
                'admin_message': f'System error during legacy verification failure handling: {str(e)}'
            }
    
    def get_migration_statistics(self, timeframe_days: int = 30) -> Dict[str, Any]:
        """
        Generate migration statistics for monitoring and reporting.
        
        Args:
            timeframe_days (int): Number of days to look back for statistics
            
        Returns:
            Dict[str, Any]: Migration statistics
        """
        # This would typically query a database or log files
        # For now, return a template structure
        return {
            'timeframe_days': timeframe_days,
            'total_migrations': 0,  # Would be populated from actual data
            'migrations_by_type': {
                'md5_to_bcrypt': 0,
                'sha1_to_bcrypt': 0,
                'sha256_to_bcrypt': 0,
                'plain_to_bcrypt': 0
            },
            'migration_success_rate': 0.0,
            'failed_migrations': 0,
            'pending_migrations': 0,  # Users with legacy hashes who haven't logged in
            'last_updated': logging.Formatter().formatTime(logging.LogRecord(
                name='', level=0, pathname='', lineno=0, msg='', args=(), exc_info=None
            ))
        }
    
    def create_migration_audit_record(self, user_id: str, old_hash_type: str, 
                                    new_hash_type: str, success: bool, 
                                    error_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a detailed audit record for password migration.
        
        Args:
            user_id (str): User identifier
            old_hash_type (str): Original hash type
            new_hash_type (str): New hash type
            success (bool): Whether migration was successful
            error_message (str, optional): Error message if migration failed
            
        Returns:
            Dict[str, Any]: Audit record
        """
        audit_record = {
            'user_id': user_id,
            'old_hash_type': old_hash_type,
            'new_hash_type': new_hash_type,
            'migration_timestamp': logging.Formatter().formatTime(logging.LogRecord(
                name='', level=0, pathname='', lineno=0, msg='', args=(), exc_info=None
            )),
            'success': success,
            'error_message': error_message
        }
        
        # Log the audit record
        self.migration_logger.info(
            f"Migration audit record created: {audit_record}",
            extra=audit_record
        )
        
        return audit_record


class LegacyPasswordHasher:
    """
    Legacy password hasher for backward compatibility.
    
    This class is maintained for compatibility with existing code.
    New code should use the LegacyPasswordHandler class instead.
    """
    
    @staticmethod
    def verify_legacy_hash(password, hash_str, hash_type='md5'):
        """
        Verify password against legacy hash formats (legacy interface)
        
        Args:
            password (str): Plain text password
            hash_str (str): Legacy hash string
            hash_type (str): Type of legacy hash (md5, sha1, sha256)
            
        Returns:
            bool: True if password matches hash
        """
        # Use the new handler for actual verification
        handler = LegacyPasswordHandler()
        return handler.verify_legacy_hash(password, hash_str, hash_type)
    
    @staticmethod
    def migrate_legacy_password(password, legacy_hash, legacy_type='md5'):
        """
        Migrate legacy password to bcrypt (legacy interface)
        
        Args:
            password (str): Plain text password
            legacy_hash (str): Legacy hash string
            legacy_type (str): Type of legacy hash
            
        Returns:
            str or None: New bcrypt hash if migration successful, None otherwise
        """
        # Use the new handler for actual migration
        handler = LegacyPasswordHandler()
        return handler.migrate_to_secure_hash(password, legacy_hash)


from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import re
import string


@dataclass
class ValidationResult:
    """
    Result of password validation containing validation status and feedback.
    """
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    strength_score: int  # 0-100
    strength_level: str  # "weak", "medium", "strong"
    suggestions: List[str]


class PasswordValidator:
    """
    Comprehensive password validation system that enforces security requirements with performance optimizations.
    
    This validator implements all password strength requirements from the specification:
    - Minimum length requirements
    - Character variety requirements (uppercase, lowercase, numbers, special chars)
    - Common password blacklist checking
    - Sequential and repeated character detection
    - User similarity checking
    - Specific improvement suggestions
    - Comprehensive error handling and recovery mechanisms
    - Performance optimizations with caching
    - Thread-safe validation operations
    
    Requirements addressed: 2.1, 2.2, 2.3, 2.4, 2.5, 4.1, 4.4, 7.1, 7.4
    """
    
    def __init__(self, min_length: int = 8, max_length: int = 128):
        """
        Initialize password validator with configuration, error handling, and performance optimizations.
        
        Args:
            min_length: Minimum password length (default: 8)
            max_length: Maximum password length (default: 128)
        """
        self.min_length = min_length
        self.max_length = max_length
        
        # Initialize error handler
        self.error_handler = get_error_handler()
        
        # Initialize performance components
        self.performance_monitor = get_performance_monitor()
        self.validation_cache = get_password_validation_cache()
        
        # Get cached validation rules
        self.validation_rules = self.validation_cache.get_validation_rules()
        
        # Get cached common passwords
        self.common_passwords = self.validation_cache.get_common_passwords()
        
        # Special characters from cached rules
        self.SPECIAL_CHARS = self.validation_rules.get('special_chars', "!@#$%^&*()_+-=[]{}|;:,.<>?~`")
        
        # Log validator initialization
        logger.info(f"PasswordValidator initialized with min_length={min_length}, max_length={max_length}")
    
    @performance_tracked('password_validator.validate')
    def validate(self, password: str, user: Optional[Any] = None) -> ValidationResult:
        """
        Comprehensive password validation with enhanced error handling and performance optimizations.
        
        Args:
            password: Password to validate
            user: Optional user object for similarity checking
            
        Returns:
            ValidationResult: Complete validation result with errors, warnings, and suggestions
            
        Raises:
            ValidationError: If validation encounters system errors
        """
        try:
            # Input validation with comprehensive error handling
            if not isinstance(password, str):
                validation_error = ValidationError(
                    validation_errors=["Password must be a string"],
                    suggestions=["Provide a valid string password"],
                    strength_score=0,
                    user_context={
                        'operation': 'password_validation',
                        'user_id': getattr(user, 'id', 'unknown') if user else 'unknown',
                        'input_type': type(password).__name__
                    }
                )
                raise validation_error
            
            # Check cache for password strength (using hash for privacy)
            password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            cached_result = self.validation_cache.calculate_strength_score(password_hash)
            
            # If we have a cached result and it's recent, use it
            if cached_result and cached_result.get('score', 0) > 0:
                return ValidationResult(
                    is_valid=cached_result.get('score', 0) >= 60,
                    errors=cached_result.get('checks_failed', []),
                    warnings=[],
                    strength_score=cached_result.get('score', 0),
                    strength_level=cached_result.get('level', 'weak'),
                    suggestions=cached_result.get('suggestions', [])
                )
            
            errors = []
            warnings = []
            suggestions = []
            score = 0
            
            # Use cached validation rules
            rules = self.validation_rules
            
            # Length validation
            length_result = self.check_length(password)
            if not length_result:
                errors.append(f"Password must be at least {rules['min_length']} characters long")
                suggestions.append(f"Add more characters to reach minimum {rules['min_length']} characters")
            else:
                score += 15  # Base score for meeting length requirement
                
            if len(password) > rules['max_length']:
                errors.append(f"Password must not exceed {rules['max_length']} characters")
            
            # Character variety validation using cached rules
            char_variety = self.check_character_variety(password)
            
            if rules.get('require_lowercase', True) and not char_variety.get('has_lowercase', False):
                errors.append("Password must contain at least one lowercase letter")
                suggestions.append("Add lowercase letters (a-z)")
            else:
                score += 15
                
            if rules.get('require_uppercase', True) and not char_variety.get('has_uppercase', False):
                errors.append("Password must contain at least one uppercase letter")
                suggestions.append("Add uppercase letters (A-Z)")
            else:
                score += 15
                
            if rules.get('require_numbers', True) and not char_variety.get('has_digits', False):
                errors.append("Password must contain at least one number")
                suggestions.append("Add numbers (0-9)")
            else:
                score += 15
                
            if rules.get('require_special_chars', True) and not char_variety.get('has_special', False):
                errors.append("Password must contain at least one special character")
                suggestions.append(f"Add special characters ({self.SPECIAL_CHARS[:10]}...)")
            else:
                score += 15
            
            # Bonus points for character variety
            variety_count = sum(1 for v in char_variety.values() if v)
            if variety_count == 4:
                score += 10  # Bonus for all character types
            
            # Common password check using cached blacklist
            if not self.check_common_passwords(password):
                errors.append("Password is too common and easily guessable")
                suggestions.append("Use a more unique password that's not commonly used")
                score = max(0, score - 20)
            else:
                score += 10
            
            # Sequential patterns check
            if rules.get('check_sequential_patterns', True) and not self.check_sequential_patterns(password):
                warnings.append("Password contains sequential characters which may be less secure")
                suggestions.append("Avoid sequential characters like 'abc' or '123'")
                score = max(0, score - 5)
            
            # Repeated characters check
            repeated_info = self._check_repeated_chars(password, rules.get('max_repeated_chars', 3))
            if repeated_info['has_excessive_repeats']:
                warnings.append("Password contains too many repeated characters")
                suggestions.append("Reduce repeated characters for better security")
                score = max(0, score - 5)
            
            # User similarity check
            if user is not None and rules.get('check_user_similarity', True):
                if not self.check_user_similarity(password, user):
                    errors.append("Password is too similar to user information")
                    suggestions.append("Use a password that doesn't contain your personal information")
                    score = max(0, score - 15)
            
            # Additional complexity bonuses
            if len(password) >= 12:
                score += 5  # Bonus for longer passwords
            if len(password) >= 16:
                score += 5  # Additional bonus for very long passwords
                
            # Mixed case bonus
            if (any(c.isupper() for c in password) and 
                any(c.islower() for c in password) and
                any(c.isdigit() for c in password) and
                any(c in self.SPECIAL_CHARS for c in password)):
                score += 5  # Bonus for good mixing
            
            # Ensure score is within bounds
            score = max(0, min(100, score))
            
            # Determine strength level
            if score >= 80:
                strength_level = "strong"
            elif score >= 60:
                strength_level = "medium"
            else:
                strength_level = "weak"
            
            # Add general suggestions if password is weak
            if strength_level == "weak" and not suggestions:
                suggestions.extend([
                    "Use a longer password with mixed character types",
                    "Avoid common words and patterns",
                    "Consider using a passphrase with special characters"
                ])
            
            is_valid = len(errors) == 0
            
            # Cache the result for future use
            cache_result = {
                'score': score,
                'level': strength_level,
                'checks_passed': [],
                'checks_failed': errors,
                'suggestions': suggestions
            }
            # Note: In a real implementation, we would cache this result
            
            # Log validation attempt (without sensitive data)
            logger.debug(f"Password validation completed: valid={is_valid}, score={score}, level={strength_level}")
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                strength_score=score,
                strength_level=strength_level,
                suggestions=suggestions
            )
            
        except ValidationError:
            # Re-raise validation errors
            raise
        except Exception as e:
            # Handle unexpected system errors during validation
            system_error = self.error_handler.handle_system_error(
                error=e,
                operation='password_validation',
                user_context={
                    'user_id': getattr(user, 'id', 'unknown') if user else 'unknown',
                    'password_length': len(password) if isinstance(password, str) else 0
                }
            )
            raise system_error
    
    @performance_tracked('password_validator.check_common_passwords')
    def check_common_passwords(self, password: str) -> bool:
        """
        Check if password is in the cached common passwords blacklist.
        
        Args:
            password: Password to check
            
        Returns:
            bool: True if password is NOT in blacklist (i.e., is acceptable)
        """
        # Use cached common passwords for better performance
        common_passwords = self.common_passwords
        
        # Check exact match (case insensitive)
        if password.lower() in common_passwords:
            return False
        
        # Check if password is just a common password with numbers appended
        for common in common_passwords:
            if password.lower().startswith(common) and password[len(common):].isdigit():
                return False
        
        # Check for common patterns
        common_patterns = [
            r'^password\d*$',  # password + numbers
            r'^\d{4,}$',       # only numbers (4+ digits)
            r'^[a-z]+\d{1,4}$', # word + 1-4 numbers
            r'^qwerty\d*$',    # qwerty + numbers
            r'^abc\d*$',       # abc + numbers
        ]
        
        for pattern in common_patterns:
            if re.match(pattern, password.lower()):
                return False
        
        return True
    
    def check_length(self, password: str) -> bool:
        """
        Check if password meets length requirements.
        
        Args:
            password: Password to check
            
        Returns:
            bool: True if password meets length requirements
        """
        rules = self.validation_rules
        min_length = rules.get('min_length', self.min_length)
        max_length = rules.get('max_length', self.max_length)
        return min_length <= len(password) <= max_length
    
    def check_character_variety(self, password: str) -> Dict[str, bool]:
        """
        Check password for character variety requirements.
        
        Args:
            password: Password to check
            
        Returns:
            Dict[str, bool]: Dictionary with boolean flags for each character type
        """
        return {
            'has_lowercase': any(c.islower() for c in password),
            'has_uppercase': any(c.isupper() for c in password),
            'has_digits': any(c.isdigit() for c in password),
            'has_special': any(c in self.SPECIAL_CHARS for c in password)
        }
    
    def check_sequential_patterns(self, password: str) -> bool:
        """
        Check for sequential character patterns.
        
        Args:
            password: Password to check
            
        Returns:
            bool: True if password does NOT contain problematic sequential patterns
        """
        return not self._has_sequential_chars(password, min_length=3)
    
    def check_user_similarity(self, password: str, user: Any) -> bool:
        """
        Check if password is too similar to user information.
        
        Args:
            password: Password to check
            user: User object with personal information
            
        Returns:
            bool: True if password is NOT too similar to user info
        """
        if user is None:
            return True
        
        # Get user information fields to check against
        user_info = []
        
        # Common user fields to check
        user_fields = ['username', 'email', 'first_name', 'last_name', 'name']
        
        for field in user_fields:
            if hasattr(user, field):
                value = getattr(user, field)
                if value and isinstance(value, str):
                    user_info.append(value.lower())
                    # Also add parts of email (before @)
                    if field == 'email' and '@' in value:
                        user_info.append(value.split('@')[0].lower())
        
        # Check if password contains any user information
        password_lower = password.lower()
        
        for info in user_info:
            if len(info) >= 3:  # Only check meaningful strings
                if info in password_lower or password_lower in info:
                    return False
                
                # Check for partial matches (50% or more overlap)
                if len(info) >= 4:
                    for i in range(len(info) - 2):
                        substr = info[i:i+3]
                        if substr in password_lower:
                            return False
        
        return True
    
    def _has_sequential_chars(self, password: str, min_length: int = 3) -> bool:
        """
        Check for sequential characters in password.
        
        Args:
            password: Password to check
            min_length: Minimum length of sequential pattern to detect
            
        Returns:
            bool: True if sequential characters found
        """
        for i in range(len(password) - min_length + 1):
            substr = password[i:i + min_length]
            
            # Check for numeric sequences (123, 456, etc.)
            if substr.isdigit():
                if all(ord(substr[j]) == ord(substr[0]) + j for j in range(len(substr))):
                    return True
                # Check for reverse sequences (321, 654, etc.)
                if all(ord(substr[j]) == ord(substr[0]) - j for j in range(len(substr))):
                    return True
            
            # Check for alphabetic sequences (abc, def, etc.)
            if substr.isalpha():
                substr_lower = substr.lower()
                if all(ord(substr_lower[j]) == ord(substr_lower[0]) + j for j in range(len(substr_lower))):
                    return True
                # Check for reverse sequences (cba, fed, etc.)
                if all(ord(substr_lower[j]) == ord(substr_lower[0]) - j for j in range(len(substr_lower))):
                    return True
            
            # Check for keyboard sequences (qwe, asd, zxc, etc.)
            keyboard_rows = [
                'qwertyuiop',
                'asdfghjkl',
                'zxcvbnm',
                '1234567890'
            ]
            
            for row in keyboard_rows:
                if substr.lower() in row:
                    return True
                # Check reverse keyboard sequences
                if substr.lower() in row[::-1]:
                    return True
        
        return False
    
    def _check_repeated_chars(self, password: str, max_repeat: int = 3) -> Dict[str, Any]:
        """
        Check for excessive repeated characters.
        
        Args:
            password: Password to check
            max_repeat: Maximum allowed consecutive repeats
            
        Returns:
            Dict with repeat analysis
        """
        # Check for consecutive repeated characters
        consecutive_repeats = 0
        max_consecutive = 0
        current_char = None
        current_count = 0
        
        for char in password:
            if char == current_char:
                current_count += 1
                max_consecutive = max(max_consecutive, current_count)
            else:
                current_char = char
                current_count = 1
        
        # Check for overall character frequency
        char_frequency = {}
        for char in password:
            char_frequency[char] = char_frequency.get(char, 0) + 1
        
        max_frequency = max(char_frequency.values()) if char_frequency else 0
        
        return {
            'has_excessive_repeats': max_consecutive > max_repeat or max_frequency > len(password) // 2,
            'max_consecutive': max_consecutive,
            'max_frequency': max_frequency,
            'char_frequency': char_frequency
        }
    
    def check_sequential_patterns(self, password: str) -> bool:
        """
        Check for sequential character patterns.
        
        Args:
            password: Password to check
            
        Returns:
            bool: True if password does NOT contain problematic sequential patterns
        """
        return not self._has_sequential_chars(password, min_length=3)
    
    def check_user_similarity(self, password: str, user: Any) -> bool:
        """
        Check if password is too similar to user information.
        
        Args:
            password: Password to check
            user: User object with personal information
            
        Returns:
            bool: True if password is NOT too similar to user info
        """
        if user is None:
            return True
        
        # Get user information fields to check against
        user_info = []
        
        # Common user fields to check
        user_fields = ['username', 'email', 'first_name', 'last_name', 'name']
        
        for field in user_fields:
            if hasattr(user, field):
                value = getattr(user, field)
                if value and isinstance(value, str):
                    user_info.append(value.lower())
                    # Also add parts of email (before @)
                    if field == 'email' and '@' in value:
                        user_info.append(value.split('@')[0].lower())
        
        # Check if password contains any user information
        password_lower = password.lower()
        
        for info in user_info:
            if len(info) >= 3:  # Only check meaningful strings
                if info in password_lower or password_lower in info:
                    return False
                
                # Check for partial matches (50% or more overlap)
                if len(info) >= 4:
                    for i in range(len(info) - 2):
                        substr = info[i:i+3]
                        if substr in password_lower:
                            return False
        
        return True
    
    def _has_sequential_chars(self, password: str, min_length: int = 3) -> bool:
        """
        Check for sequential characters in password.
        
        Args:
            password: Password to check
            min_length: Minimum length of sequential pattern to detect
            
        Returns:
            bool: True if sequential characters found
        """
        for i in range(len(password) - min_length + 1):
            substr = password[i:i + min_length]
            
            # Check for numeric sequences (123, 456, etc.)
            if substr.isdigit():
                if all(ord(substr[j]) == ord(substr[0]) + j for j in range(len(substr))):
                    return True
                # Check for reverse sequences (321, 654, etc.)
                if all(ord(substr[j]) == ord(substr[0]) - j for j in range(len(substr))):
                    return True
            
            # Check for alphabetic sequences (abc, def, etc.)
            if substr.isalpha():
                substr_lower = substr.lower()
                if all(ord(substr_lower[j]) == ord(substr_lower[0]) + j for j in range(len(substr_lower))):
                    return True
                # Check for reverse sequences (cba, fed, etc.)
                if all(ord(substr_lower[j]) == ord(substr_lower[0]) - j for j in range(len(substr_lower))):
                    return True
            
            # Check for keyboard sequences (qwe, asd, zxc, etc.)
            keyboard_rows = [
                'qwertyuiop',
                'asdfghjkl',
                'zxcvbnm',
                '1234567890'
            ]
            
            for row in keyboard_rows:
                if substr.lower() in row:
                    return True
                # Check reverse keyboard sequences
                if substr.lower() in row[::-1]:
                    return True
        
        return False
    
    def _check_repeated_chars(self, password: str, max_repeat: int = 3) -> Dict[str, Any]:
        """
        Check for excessive repeated characters.
        
        Args:
            password: Password to check
            max_repeat: Maximum allowed consecutive repeats
            
        Returns:
            Dict with repeat analysis
        """
        # Check for consecutive repeated characters
        consecutive_repeats = 0
        max_consecutive = 0
        current_char = None
        current_count = 0
        
        for char in password:
            if char == current_char:
                current_count += 1
                max_consecutive = max(max_consecutive, current_count)
            else:
                current_char = char
                current_count = 1
        
        # Check for overall character frequency
        char_frequency = {}
        for char in password:
            char_frequency[char] = char_frequency.get(char, 0) + 1
        
        max_frequency = max(char_frequency.values()) if char_frequency else 0
        
        return {
            'has_excessive_repeats': max_consecutive > max_repeat or max_frequency > len(password) // 2,
            'max_consecutive': max_consecutive,
            'max_frequency': max_frequency,
            'char_frequency': char_frequency
        }


class SecurePasswordValidator:
    """
    Legacy password validator for backward compatibility.
    
    This class is maintained for compatibility with existing code.
    New code should use the PasswordValidator class instead.
    """
    
    @staticmethod
    def validate_password_strength(password):
        """
        Validate password strength (legacy interface)
        
        Args:
            password (str): Password to validate
            
        Returns:
            dict: Validation result with errors and score
        """
        # Use the new validator for actual validation
        validator = PasswordValidator()
        result = validator.validate(password)
        
        # Convert to legacy format
        return {
            'valid': result.is_valid,
            'errors': result.errors,
            'score': result.strength_score // 10,  # Convert 0-100 to 0-10 scale
            'strength': result.strength_level
        }
    
    @staticmethod
    def _has_sequential_chars(password, min_length=3):
        """Check for sequential characters (legacy method)"""
        validator = PasswordValidator()
        return validator._has_sequential_chars(password, min_length)
    
    @staticmethod
    def _has_repeated_chars(password, max_repeat=3):
        """Check for repeated characters (legacy method)"""
        validator = PasswordValidator()
        repeat_info = validator._check_repeated_chars(password, max_repeat)
        return repeat_info['has_excessive_repeats']


@dataclass
class SecurityEvent:
    """
    Represents a security-related event for logging and monitoring.
    """
    timestamp: datetime
    event_type: str  # "auth_success", "auth_failure", "password_migration", etc.
    user_identifier: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    severity: str = "info"  # "info", "warning", "error", "critical"
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert security event to dictionary for logging."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type,
            'user_identifier': self.user_identifier,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'details': self.details or {},
            'severity': self.severity,
            'session_id': self.session_id
        }


@dataclass
class SecurityReport:
    """
    Represents a security report containing analysis and statistics.
    """
    report_id: str
    generated_at: datetime
    timeframe_start: datetime
    timeframe_end: datetime
    total_events: int
    events_by_type: Dict[str, int]
    events_by_severity: Dict[str, int]
    brute_force_attempts: int
    password_migrations: int
    failed_authentications: int
    successful_authentications: int
    unique_users: int
    unique_ips: int
    top_failure_reasons: List[Dict[str, Any]]
    security_recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert security report to dictionary."""
        return {
            'report_id': self.report_id,
            'generated_at': self.generated_at.isoformat(),
            'timeframe_start': self.timeframe_start.isoformat(),
            'timeframe_end': self.timeframe_end.isoformat(),
            'total_events': self.total_events,
            'events_by_type': self.events_by_type,
            'events_by_severity': self.events_by_severity,
            'brute_force_attempts': self.brute_force_attempts,
            'password_migrations': self.password_migrations,
            'failed_authentications': self.failed_authentications,
            'successful_authentications': self.successful_authentications,
            'unique_users': self.unique_users,
            'unique_ips': self.unique_ips,
            'top_failure_reasons': self.top_failure_reasons,
            'security_recommendations': self.security_recommendations
        }


class SecurityMonitor:
    """
    Comprehensive security monitoring and logging system for password operations.
    
    This monitor provides:
    - Comprehensive security event logging
    - Brute force attack detection
    - Security reporting functionality
    - Audit trail for password operations
    - Real-time security alerting
    - Compliance reporting
    
    Requirements addressed: 6.1, 6.2, 6.3, 6.4
    """
    
    # Event types for classification
    EVENT_TYPES = {
        'AUTH_SUCCESS': 'auth_success',
        'AUTH_FAILURE': 'auth_failure',
        'PASSWORD_MIGRATION': 'password_migration',
        'HASH_CORRUPTION': 'hash_corruption',
        'BRUTE_FORCE_DETECTED': 'brute_force_detected',
        'PASSWORD_RESET_INITIATED': 'password_reset_initiated',
        'PASSWORD_RESET_COMPLETED': 'password_reset_completed',
        'ACCOUNT_LOCKED': 'account_locked',
        'ACCOUNT_UNLOCKED': 'account_unlocked',
        'SECURITY_ERROR': 'security_error',
        'VALIDATION_FAILURE': 'validation_failure',
        'LEGACY_HASH_DETECTED': 'legacy_hash_detected',
        'SYSTEM_ERROR': 'system_error'
    }
    
    # Severity levels
    SEVERITY_LEVELS = {
        'INFO': 'info',
        'WARNING': 'warning', 
        'ERROR': 'error',
        'CRITICAL': 'critical'
    }
    
    def __init__(self, brute_force_threshold: int = 5, brute_force_window_minutes: int = 15):
        """
        Initialize security monitor with configuration, error handler integration, and performance optimizations.
        
        Args:
            brute_force_threshold: Number of failed attempts before brute force detection
            brute_force_window_minutes: Time window for brute force detection
        """
        self.brute_force_threshold = brute_force_threshold
        self.brute_force_window = timedelta(minutes=brute_force_window_minutes)
        
        # Initialize loggers
        self.security_logger = logging.getLogger('security')
        self.audit_logger = logging.getLogger('security.audit')
        self.alert_logger = logging.getLogger('security.alerts')
        
        # In-memory storage for recent events (for brute force detection)
        # In production, this should be backed by Redis or database
        self._recent_events = []
        self._max_recent_events = 10000  # Limit memory usage
        
        # Initialize performance components
        self.performance_monitor = get_performance_monitor()
        self.db_manager = get_db_connection_manager()
        
        # Initialize error handler integration
        self._setup_error_handler_integration()
        
        self.security_logger.info("SecurityMonitor initialized", extra={
            'brute_force_threshold': brute_force_threshold,
            'brute_force_window_minutes': brute_force_window_minutes
        })
    
    def _setup_error_handler_integration(self):
        """
        Set up integration with the error handler system.
        
        This ensures that the SecurityMonitor is available to the error handler
        for comprehensive error logging and monitoring.
        """
        try:
            # Get the global error handler and set this monitor
            error_handler = get_error_handler()
            error_handler.set_security_monitor(self)
            
            self.security_logger.debug("Error handler integration established")
        except Exception as e:
            self.security_logger.warning(f"Failed to establish error handler integration: {str(e)}")
    
    @performance_tracked('security_monitor.log_authentication_attempt')
    def log_authentication_attempt(self, user: str, success: bool, details: Optional[Dict] = None) -> None:
        """
        Log authentication attempt with comprehensive details.
        
        Args:
            user: User identifier (username, email, or user ID)
            success: Whether authentication was successful
            details: Additional context (IP, user agent, error details, etc.)
        
        Requirements: 6.1 - Log password hashing errors with timestamp and user context
        """
        try:
            event_type = self.EVENT_TYPES['AUTH_SUCCESS'] if success else self.EVENT_TYPES['AUTH_FAILURE']
            severity = self.SEVERITY_LEVELS['INFO'] if success else self.SEVERITY_LEVELS['WARNING']
            
            # Extract details
            details = details or {}
            ip_address = details.get('ip_address')
            user_agent = details.get('user_agent')
            error_message = details.get('error_message')
            session_id = details.get('session_id')
            
            # Create security event
            event = SecurityEvent(
                timestamp=datetime.now(),
                event_type=event_type,
                user_identifier=user,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    'success': success,
                    'error_message': error_message,
                    'authentication_method': details.get('auth_method', 'password'),
                    'client_info': details.get('client_info'),
                    'request_path': details.get('request_path')
                },
                severity=severity,
                session_id=session_id
            )
            
            # Log the event
            self._log_security_event(event)
            
            # Store for brute force detection
            self._store_recent_event(event)
            
            # Check for brute force if authentication failed
            if not success:
                self._check_brute_force_attempts(user, ip_address)
            
            # Log specific success/failure message
            if success:
                self.security_logger.info(
                    f"Authentication successful for user: {user}",
                    extra=event.to_dict()
                )
            else:
                self.security_logger.warning(
                    f"Authentication failed for user: {user} - {error_message or 'Unknown error'}",
                    extra=event.to_dict()
                )
                
        except Exception as e:
            self.security_logger.error(f"Error logging authentication attempt: {str(e)}")
    
    @performance_tracked('security_monitor.log_password_migration')
    def log_password_migration(self, user: str, from_type: str, to_type: str, success: bool = True, 
                             details: Optional[Dict] = None) -> None:
        """
        Log password migration events with audit trail.
        
        Args:
            user: User identifier
            from_type: Original password hash type (md5, sha1, sha256, etc.)
            to_type: New password hash type (usually secure_bcrypt)
            success: Whether migration was successful
            details: Additional context
        
        Requirements: 6.2 - Log successful password migrations from legacy formats
        """
        try:
            event_type = self.EVENT_TYPES['PASSWORD_MIGRATION']
            severity = self.SEVERITY_LEVELS['INFO'] if success else self.SEVERITY_LEVELS['ERROR']
            
            details = details or {}
            
            event = SecurityEvent(
                timestamp=datetime.now(),
                event_type=event_type,
                user_identifier=user,
                ip_address=details.get('ip_address'),
                user_agent=details.get('user_agent'),
                details={
                    'from_hash_type': from_type,
                    'to_hash_type': to_type,
                    'migration_success': success,
                    'migration_reason': details.get('reason', 'automatic_login'),
                    'error_message': details.get('error_message') if not success else None,
                    'migration_id': details.get('migration_id')
                },
                severity=severity,
                session_id=details.get('session_id')
            )
            
            # Log the event
            self._log_security_event(event)
            
            # Create audit trail entry
            self.audit_logger.info(
                f"Password migration {'completed' if success else 'failed'}: "
                f"user={user}, {from_type} -> {to_type}",
                extra=event.to_dict()
            )
            
            if success:
                self.security_logger.info(
                    f"Password migration successful: user={user}, {from_type} -> {to_type}",
                    extra=event.to_dict()
                )
            else:
                self.security_logger.error(
                    f"Password migration failed: user={user}, {from_type} -> {to_type} - "
                    f"{details.get('error_message', 'Unknown error')}",
                    extra=event.to_dict()
                )
                
        except Exception as e:
            self.security_logger.error(f"Error logging password migration: {str(e)}")
    
    def log_security_error(self, error: Exception, context: Optional[Dict] = None) -> None:
        """
        Log security-related errors with full context.
        
        Args:
            error: Exception that occurred
            context: Additional context (user, operation, etc.)
        
        Requirements: 6.1 - Log password hashing errors with timestamp and user context
        """
        try:
            context = context or {}
            error_type = type(error).__name__
            error_message = str(error)
            
            # Determine event type based on error
            if 'salt' in error_message.lower() or 'hash' in error_message.lower():
                event_type = self.EVENT_TYPES['HASH_CORRUPTION']
                severity = self.SEVERITY_LEVELS['CRITICAL']
            elif 'validation' in error_message.lower():
                event_type = self.EVENT_TYPES['VALIDATION_FAILURE']
                severity = self.SEVERITY_LEVELS['WARNING']
            else:
                event_type = self.EVENT_TYPES['SECURITY_ERROR']
                severity = self.SEVERITY_LEVELS['ERROR']
            
            event = SecurityEvent(
                timestamp=datetime.now(),
                event_type=event_type,
                user_identifier=context.get('user', 'unknown'),
                ip_address=context.get('ip_address'),
                user_agent=context.get('user_agent'),
                details={
                    'error_type': error_type,
                    'error_message': error_message,
                    'operation': context.get('operation'),
                    'stack_trace': context.get('stack_trace'),
                    'request_data': context.get('request_data'),
                    'system_info': context.get('system_info')
                },
                severity=severity,
                session_id=context.get('session_id')
            )
            
            # Log the event
            self._log_security_event(event)
            
            # Log with appropriate severity
            if severity == self.SEVERITY_LEVELS['CRITICAL']:
                self.security_logger.critical(
                    f"Critical security error: {error_type} - {error_message}",
                    extra=event.to_dict()
                )
                # Also send to alerts
                self.alert_logger.critical(
                    f"CRITICAL SECURITY ALERT: {error_type} - {error_message}",
                    extra=event.to_dict()
                )
            else:
                self.security_logger.error(
                    f"Security error: {error_type} - {error_message}",
                    extra=event.to_dict()
                )
                
        except Exception as e:
            # Fallback logging if security logging fails
            logger.error(f"Critical error in security logging: {str(e)}")
    
    def detect_brute_force_attempts(self, user: str, timeframe: Optional[timedelta] = None) -> bool:
        """
        Detect brute force attempts for a specific user.
        
        Args:
            user: User identifier to check
            timeframe: Time window to check (uses default if None)
        
        Returns:
            bool: True if brute force attempt detected
        
        Requirements: 6.3 - Log multiple authentication failures and brute force attempts
        """
        try:
            timeframe = timeframe or self.brute_force_window
            cutoff_time = datetime.now() - timeframe
            
            # Count failed authentication attempts in timeframe
            failed_attempts = 0
            for event in self._recent_events:
                if (event.user_identifier == user and 
                    event.event_type == self.EVENT_TYPES['AUTH_FAILURE'] and
                    event.timestamp >= cutoff_time):
                    failed_attempts += 1
            
            return failed_attempts >= self.brute_force_threshold
            
        except Exception as e:
            self.security_logger.error(f"Error detecting brute force attempts: {str(e)}")
            return False
    
    @performance_tracked('security_monitor.generate_security_report')
    def generate_security_report(self, timeframe: timedelta) -> SecurityReport:
        """
        Generate comprehensive security report for specified timeframe.
        
        Args:
            timeframe: Time period to analyze
        
        Returns:
            SecurityReport: Comprehensive security analysis
        
        Requirements: 6.4 - Generate security reports on password strength compliance
        """
        try:
            end_time = datetime.now()
            start_time = end_time - timeframe
            
            # Filter events in timeframe
            relevant_events = [
                event for event in self._recent_events
                if start_time <= event.timestamp <= end_time
            ]
            
            # Analyze events
            events_by_type = {}
            events_by_severity = {}
            unique_users = set()
            unique_ips = set()
            brute_force_count = 0
            migration_count = 0
            failed_auth_count = 0
            successful_auth_count = 0
            failure_reasons = {}
            
            for event in relevant_events:
                # Count by type
                events_by_type[event.event_type] = events_by_type.get(event.event_type, 0) + 1
                
                # Count by severity
                events_by_severity[event.severity] = events_by_severity.get(event.severity, 0) + 1
                
                # Track unique users and IPs
                unique_users.add(event.user_identifier)
                if event.ip_address:
                    unique_ips.add(event.ip_address)
                
                # Count specific event types
                if event.event_type == self.EVENT_TYPES['BRUTE_FORCE_DETECTED']:
                    brute_force_count += 1
                elif event.event_type == self.EVENT_TYPES['PASSWORD_MIGRATION']:
                    migration_count += 1
                elif event.event_type == self.EVENT_TYPES['AUTH_FAILURE']:
                    failed_auth_count += 1
                    # Track failure reasons
                    error_msg = event.details.get('error_message', 'Unknown') if event.details else 'Unknown'
                    failure_reasons[error_msg] = failure_reasons.get(error_msg, 0) + 1
                elif event.event_type == self.EVENT_TYPES['AUTH_SUCCESS']:
                    successful_auth_count += 1
            
            # Generate top failure reasons
            top_failure_reasons = [
                {'reason': reason, 'count': count}
                for reason, count in sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True)[:10]
            ]
            
            # Generate security recommendations
            recommendations = self._generate_security_recommendations(
                events_by_type, events_by_severity, brute_force_count, 
                failed_auth_count, successful_auth_count
            )
            
            # Create report
            report = SecurityReport(
                report_id=f"security_report_{int(end_time.timestamp())}",
                generated_at=end_time,
                timeframe_start=start_time,
                timeframe_end=end_time,
                total_events=len(relevant_events),
                events_by_type=events_by_type,
                events_by_severity=events_by_severity,
                brute_force_attempts=brute_force_count,
                password_migrations=migration_count,
                failed_authentications=failed_auth_count,
                successful_authentications=successful_auth_count,
                unique_users=len(unique_users),
                unique_ips=len(unique_ips),
                top_failure_reasons=top_failure_reasons,
                security_recommendations=recommendations
            )
            
            # Log report generation
            self.security_logger.info(
                f"Security report generated: {report.report_id}",
                extra=report.to_dict()
            )
            
            return report
            
        except Exception as e:
            self.security_logger.error(f"Error generating security report: {str(e)}")
            # Return empty report on error
            return SecurityReport(
                report_id=f"error_report_{int(datetime.now().timestamp())}",
                generated_at=datetime.now(),
                timeframe_start=datetime.now() - timeframe,
                timeframe_end=datetime.now(),
                total_events=0,
                events_by_type={},
                events_by_severity={},
                brute_force_attempts=0,
                password_migrations=0,
                failed_authentications=0,
                successful_authentications=0,
                unique_users=0,
                unique_ips=0,
                top_failure_reasons=[],
                security_recommendations=["Error generating report - check system logs"]
            )
    
    def _log_security_event(self, event: SecurityEvent) -> None:
        """
        Internal method to log security events to appropriate loggers.
        
        Args:
            event: SecurityEvent to log
        """
        try:
            # Log to main security logger
            log_data = event.to_dict()
            
            if event.severity == self.SEVERITY_LEVELS['CRITICAL']:
                self.security_logger.critical(f"Security event: {event.event_type}", extra=log_data)
            elif event.severity == self.SEVERITY_LEVELS['ERROR']:
                self.security_logger.error(f"Security event: {event.event_type}", extra=log_data)
            elif event.severity == self.SEVERITY_LEVELS['WARNING']:
                self.security_logger.warning(f"Security event: {event.event_type}", extra=log_data)
            else:
                self.security_logger.info(f"Security event: {event.event_type}", extra=log_data)
            
            # Log to audit trail for certain event types
            audit_events = [
                self.EVENT_TYPES['PASSWORD_MIGRATION'],
                self.EVENT_TYPES['ACCOUNT_LOCKED'],
                self.EVENT_TYPES['ACCOUNT_UNLOCKED'],
                self.EVENT_TYPES['PASSWORD_RESET_COMPLETED']
            ]
            
            if event.event_type in audit_events:
                self.audit_logger.info(f"Audit: {event.event_type}", extra=log_data)
                
        except Exception as e:
            # Fallback to basic logging if structured logging fails
            logger.error(f"Failed to log security event: {str(e)}")
    
    def _store_recent_event(self, event: SecurityEvent) -> None:
        """
        Store event in memory for brute force detection.
        
        Args:
            event: SecurityEvent to store
        """
        try:
            self._recent_events.append(event)
            
            # Limit memory usage by removing old events
            if len(self._recent_events) > self._max_recent_events:
                # Remove oldest 10% of events
                remove_count = self._max_recent_events // 10
                self._recent_events = self._recent_events[remove_count:]
            
            # Also remove events older than 24 hours to prevent memory bloat
            cutoff_time = datetime.now() - timedelta(hours=24)
            self._recent_events = [
                e for e in self._recent_events if e.timestamp >= cutoff_time
            ]
            
        except Exception as e:
            self.security_logger.error(f"Error storing recent event: {str(e)}")
    
    def _check_brute_force_attempts(self, user: str, ip_address: Optional[str] = None) -> None:
        """
        Check for brute force attempts and log alerts if detected.
        
        Args:
            user: User identifier
            ip_address: IP address of the attempt
        """
        try:
            # Check user-based brute force
            if self.detect_brute_force_attempts(user):
                self._log_brute_force_detection(user, ip_address, 'user_based')
            
            # Check IP-based brute force if IP is available
            if ip_address:
                if self._detect_ip_brute_force(ip_address):
                    self._log_brute_force_detection(user, ip_address, 'ip_based')
                    
        except Exception as e:
            self.security_logger.error(f"Error checking brute force attempts: {str(e)}")
    
    def _detect_ip_brute_force(self, ip_address: str) -> bool:
        """
        Detect brute force attempts from a specific IP address.
        
        Args:
            ip_address: IP address to check
        
        Returns:
            bool: True if brute force detected from this IP
        """
        try:
            cutoff_time = datetime.now() - self.brute_force_window
            
            failed_attempts = 0
            for event in self._recent_events:
                if (event.ip_address == ip_address and 
                    event.event_type == self.EVENT_TYPES['AUTH_FAILURE'] and
                    event.timestamp >= cutoff_time):
                    failed_attempts += 1
            
            return failed_attempts >= self.brute_force_threshold
            
        except Exception as e:
            self.security_logger.error(f"Error detecting IP brute force: {str(e)}")
            return False
    
    def _log_brute_force_detection(self, user: str, ip_address: Optional[str], detection_type: str) -> None:
        """
        Log brute force detection with alert.
        
        Args:
            user: User identifier
            ip_address: IP address involved
            detection_type: Type of detection (user_based, ip_based)
        """
        try:
            event = SecurityEvent(
                timestamp=datetime.now(),
                event_type=self.EVENT_TYPES['BRUTE_FORCE_DETECTED'],
                user_identifier=user,
                ip_address=ip_address,
                details={
                    'detection_type': detection_type,
                    'threshold': self.brute_force_threshold,
                    'window_minutes': self.brute_force_window.total_seconds() / 60,
                    'recommended_action': 'Consider account lockout or IP blocking'
                },
                severity=self.SEVERITY_LEVELS['CRITICAL']
            )
            
            self._log_security_event(event)
            
            # Send alert
            self.alert_logger.critical(
                f"BRUTE FORCE DETECTED: {detection_type} - user={user}, ip={ip_address}",
                extra=event.to_dict()
            )
            
        except Exception as e:
            self.security_logger.error(f"Error logging brute force detection: {str(e)}")
    
    def _generate_security_recommendations(self, events_by_type: Dict, events_by_severity: Dict,
                                         brute_force_count: int, failed_auth_count: int,
                                         successful_auth_count: int) -> List[str]:
        """
        Generate security recommendations based on event analysis.
        
        Args:
            events_by_type: Count of events by type
            events_by_severity: Count of events by severity
            brute_force_count: Number of brute force attempts
            failed_auth_count: Number of failed authentications
            successful_auth_count: Number of successful authentications
        
        Returns:
            List[str]: Security recommendations
        """
        recommendations = []
        
        try:
            # Check brute force activity
            if brute_force_count > 0:
                recommendations.append(
                    f"High Priority: {brute_force_count} brute force attempts detected. "
                    "Consider implementing account lockout policies and IP blocking."
                )
            
            # Check failure rate
            total_auth = failed_auth_count + successful_auth_count
            if total_auth > 0:
                failure_rate = failed_auth_count / total_auth
                if failure_rate > 0.3:  # More than 30% failure rate
                    recommendations.append(
                        f"High failure rate detected ({failure_rate:.1%}). "
                        "Review authentication mechanisms and user education."
                    )
            
            # Check for critical events
            critical_count = events_by_severity.get(self.SEVERITY_LEVELS['CRITICAL'], 0)
            if critical_count > 0:
                recommendations.append(
                    f"{critical_count} critical security events detected. "
                    "Immediate investigation required."
                )
            
            # Check for hash corruption
            hash_corruption_count = events_by_type.get(self.EVENT_TYPES['HASH_CORRUPTION'], 0)
            if hash_corruption_count > 0:
                recommendations.append(
                    f"{hash_corruption_count} hash corruption events detected. "
                    "Review password storage and migration procedures."
                )
            
            # Check migration activity
            migration_count = events_by_type.get(self.EVENT_TYPES['PASSWORD_MIGRATION'], 0)
            if migration_count > 0:
                recommendations.append(
                    f"{migration_count} password migrations completed. "
                    "Monitor migration progress and user experience."
                )
            
            # General recommendations
            if not recommendations:
                recommendations.append("No immediate security concerns detected. Continue monitoring.")
            
            recommendations.append("Regularly review security logs and update security policies.")
            recommendations.append("Ensure all users are using strong passwords and MFA where possible.")
            
        except Exception as e:
            recommendations.append(f"Error generating recommendations: {str(e)}")
        
        return recommendations


# Global security monitor instance
_security_monitor = None

def get_security_monitor() -> SecurityMonitor:
    """
    Get global security monitor instance (singleton pattern).
    
    Returns:
        SecurityMonitor: Global security monitor instance
    """
    global _security_monitor
    if _security_monitor is None:
        _security_monitor = SecurityMonitor()
    return _security_monitor


# Utility functions for easy use
def hash_password(password, rounds=12):
    """
    Hash password using bcrypt
    
    Args:
        password (str): Plain text password
        rounds (int): Number of salt rounds
        
    Returns:
        str: Bcrypt hash string
    """
    return NodeJSCompatiblePasswordHasher.hash_password(password, rounds)


def verify_password(password, hash_str):
    """
    Verify password against hash with enhanced legacy support and security monitoring
    
    Args:
        password (str): Plain text password
        hash_str (str): Hash string (bcrypt or legacy)
        
    Returns:
        bool: True if password matches
    """
    security_monitor = get_security_monitor()
    
    try:
        # Try bcrypt first
        if NodeJSCompatiblePasswordHasher.is_bcrypt_hash(hash_str):
            result = NodeJSCompatiblePasswordHasher.verify_password(password, hash_str)
            
            # Log authentication attempt
            security_monitor.log_authentication_attempt(
                user='unknown',  # User context should be provided by caller
                success=result,
                details={
                    'hash_type': 'bcrypt',
                    'verification_method': 'bcrypt_native'
                }
            )
            return result
        
        # Try secure bcrypt format
        if hash_str.startswith('secure_bcrypt$'):
            try:
                hasher = SecurePasswordHasher()
                result = hasher.verify(password, hash_str)
                
                # Log authentication attempt
                security_monitor.log_authentication_attempt(
                    user='unknown',
                    success=result,
                    details={
                        'hash_type': 'secure_bcrypt',
                        'verification_method': 'secure_hasher'
                    }
                )
                return result
            except Exception as e:
                # Log security error
                security_monitor.log_security_error(e, {
                    'operation': 'secure_bcrypt_verification',
                    'hash_type': 'secure_bcrypt'
                })
                return False
        
        # Try legacy formats using the enhanced handler
        handler = LegacyPasswordHandler()
        result = handler.verify_legacy_hash(password, hash_str)
        
        # Log legacy authentication attempt
        hash_type = handler.detect_hash_type(hash_str) or 'unknown'
        security_monitor.log_authentication_attempt(
            user='unknown',
            success=result,
            details={
                'hash_type': hash_type,
                'verification_method': 'legacy_handler',
                'requires_migration': result  # If successful, migration is needed
            }
        )
        
        return result
        
    except Exception as e:
        # Log unexpected errors
        security_monitor.log_security_error(e, {
            'operation': 'password_verification',
            'hash_type': 'unknown'
        })
        return False


def validate_password_strength(password):
    """
    Validate password strength using the comprehensive PasswordValidator
    
    Args:
        password (str): Password to validate
        
    Returns:
        dict: Validation result compatible with legacy interface
    """
    validator = PasswordValidator()
    result = validator.validate(password)
    
    # Return in legacy format for backward compatibility
    return {
        'valid': result.is_valid,
        'errors': result.errors,
        'score': result.strength_score // 10,  # Convert 0-100 to 0-10 scale
        'strength': result.strength_level,
        'warnings': result.warnings,
        'suggestions': result.suggestions
    }


def migrate_legacy_password(password, legacy_hash, user_context=None):
    """
    Migrate legacy password to secure format with comprehensive logging and security monitoring
    
    Args:
        password (str): Plain text password
        legacy_hash (str): Legacy hash string
        user_context (dict, optional): User context for logging
        
    Returns:
        str or None: New secure hash if migration successful, None otherwise
    """
    security_monitor = get_security_monitor()
    handler = LegacyPasswordHandler()
    
    try:
        # Detect legacy hash type
        legacy_type = handler.detect_hash_type(legacy_hash)
        if legacy_type is None:
            security_monitor.log_security_error(
                ValueError("Unknown legacy hash type"),
                {
                    'operation': 'legacy_password_migration',
                    'user': user_context.get('user_id', 'unknown') if user_context else 'unknown',
                    'hash_sample': legacy_hash[:8] + '...' if len(legacy_hash) > 8 else legacy_hash
                }
            )
            return None
        
        # Attempt migration
        new_hash = handler.migrate_to_secure_hash(password, legacy_hash, user_context)
        
        # Log migration attempt
        user_id = user_context.get('user_id', 'unknown') if user_context else 'unknown'
        security_monitor.log_password_migration(
            user=user_id,
            from_type=legacy_type,
            to_type='secure_bcrypt',
            success=new_hash is not None,
            details=user_context
        )
        
        return new_hash
        
    except Exception as e:
        # Log migration error
        security_monitor.log_security_error(e, {
            'operation': 'legacy_password_migration',
            'user': user_context.get('user_id', 'unknown') if user_context else 'unknown',
            'legacy_type': legacy_type if 'legacy_type' in locals() else 'unknown'
        })
        return None


def is_legacy_password_hash(hash_str):
    """
    Check if a hash string is a legacy format that needs migration
    
    Args:
        hash_str (str): Hash string to check
        
    Returns:
        bool: True if hash is a legacy format
    """
    handler = LegacyPasswordHandler()
    return handler.is_legacy_hash(hash_str)


def handle_legacy_authentication_failure(user_context=None):
    """
    Handle legacy password authentication failures with secure reset process
    
    Args:
        user_context (dict, optional): User context for logging and processing
        
    Returns:
        dict: Response with error handling instructions
    """
    handler = LegacyPasswordHandler()
    return handler.handle_legacy_verification_failure(user_context)


class PasswordSecurityController:
    """
    Central coordinator for all password security operations in the Django mall server.
    
    This controller provides a unified interface for:
    - Password hashing and verification with enhanced security
    - Password strength validation and enforcement
    - Legacy password migration and compatibility
    - Security monitoring and audit trails
    - Django authentication backend integration
    - Error handling and recovery mechanisms
    
    The controller ensures seamless integration with Django's authentication system
    while providing enhanced security features and comprehensive logging.
    
    Requirements addressed: 5.1, 5.2, 5.3, 5.4
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the password security controller with configuration.
        
        Args:
            config: Optional configuration dictionary. Uses Django settings if None.
        """
        # Load configuration from Django settings or provided config
        from django.conf import settings
        
        self.config = config or getattr(settings, 'PASSWORD_SECURITY_CONFIG', {})
        
        # Initialize components
        self.hasher = SecurePasswordHasher(rounds=self.config.get('BCRYPT_ROUNDS', 12))
        self.validator = PasswordValidator(
            min_length=self.config.get('MIN_PASSWORD_LENGTH', 8),
            max_length=self.config.get('MAX_PASSWORD_LENGTH', 128)
        )
        self.legacy_handler = LegacyPasswordHandler()
        self.security_monitor = get_security_monitor()
        
        # Configuration flags
        self.enable_legacy_migration = self.config.get('ENABLE_LEGACY_MIGRATION', True)
        self.log_security_events = self.config.get('LOG_SECURITY_EVENTS', True)
        
        # Initialize logger
        self.logger = logging.getLogger('security.controller')
        
        self.logger.info("PasswordSecurityController initialized", extra={
            'config': {k: v for k, v in self.config.items() if 'password' not in k.lower()},
            'enable_legacy_migration': self.enable_legacy_migration,
            'log_security_events': self.log_security_events
        })
    
    def hash_password(self, password: str, rounds: Optional[int] = None) -> str:
        """
        Hash password using secure bcrypt with comprehensive error handling.
        
        Args:
            password: Plain text password to hash
            rounds: Optional bcrypt rounds (uses config default if None)
            
        Returns:
            str: Secure password hash
            
        Raises:
            ValueError: If password hashing fails
            
        Requirements: 1.1, 1.4 - Secure password hashing with cryptographically secure salt
        """
        try:
            if not password or not isinstance(password, str):
                raise ValueError("Password must be a non-empty string")
            
            # Use provided rounds or config default
            hash_rounds = rounds or self.config.get('BCRYPT_ROUNDS', 12)
            
            # Create hasher with specified rounds
            if hash_rounds != self.hasher.rounds:
                hasher = SecurePasswordHasher(rounds=hash_rounds)
            else:
                hasher = self.hasher
            
            # Hash the password
            hashed = hasher.encode(password)
            
            # Log successful hash generation (without sensitive data)
            if self.log_security_events:
                self.security_monitor.log_authentication_attempt(
                    user='system',
                    success=True,
                    details={
                        'operation': 'password_hash_generation',
                        'hash_algorithm': 'secure_bcrypt',
                        'rounds': hash_rounds
                    }
                )
            
            self.logger.debug(f"Password hashed successfully with {hash_rounds} rounds")
            return hashed
            
        except Exception as e:
            # Log security error
            if self.log_security_events:
                self.security_monitor.log_security_error(e, {
                    'operation': 'password_hash_generation',
                    'rounds': rounds or self.config.get('BCRYPT_ROUNDS', 12)
                })
            
            self.logger.error(f"Password hashing failed: {str(e)}")
            raise ValueError(f"Password hashing failed: {str(e)}")
    
    def verify_password(self, password: str, hash_str: str, user_context: Optional[Dict] = None) -> bool:
        """
        Verify password against hash with legacy support and automatic migration.
        
        Args:
            password: Plain text password to verify
            hash_str: Password hash to verify against
            user_context: Optional user context for logging and migration
            
        Returns:
            bool: True if password matches hash
            
        Requirements: 1.2, 3.1, 3.2 - Multi-format verification and automatic migration
        """
        try:
            if not password or not hash_str:
                self.logger.warning("Empty password or hash provided for verification")
                return False
            
            user_id = user_context.get('user_id', 'unknown') if user_context else 'unknown'
            ip_address = user_context.get('ip_address') if user_context else None
            
            # Try secure bcrypt first
            if hash_str.startswith('secure_bcrypt$'):
                result = self.hasher.verify(password, hash_str)
                
                # Log authentication attempt
                if self.log_security_events:
                    self.security_monitor.log_authentication_attempt(
                        user=user_id,
                        success=result,
                        details={
                            'hash_type': 'secure_bcrypt',
                            'verification_method': 'secure_hasher',
                            'ip_address': ip_address
                        }
                    )
                
                return result
            
            # Try other bcrypt formats
            if NodeJSCompatiblePasswordHasher.is_bcrypt_hash(hash_str) or hash_str.startswith('bcrypt$'):
                if hash_str.startswith('bcrypt$'):
                    # Django bcrypt format
                    result = self.hasher.verify(password, hash_str)
                else:
                    # Node.js bcrypt format
                    result = NodeJSCompatiblePasswordHasher.verify_password(password, hash_str)
                
                # Log authentication attempt
                if self.log_security_events:
                    self.security_monitor.log_authentication_attempt(
                        user=user_id,
                        success=result,
                        details={
                            'hash_type': 'bcrypt',
                            'verification_method': 'bcrypt_compatible',
                            'ip_address': ip_address,
                            'requires_migration': result and self.enable_legacy_migration
                        }
                    )
                
                # If successful and migration enabled, migrate to secure format
                if result and self.enable_legacy_migration and user_context:
                    try:
                        new_hash = self.hash_password(password)
                        user_context['new_hash'] = new_hash
                        
                        # Log migration
                        if self.log_security_events:
                            self.security_monitor.log_password_migration(
                                user=user_id,
                                from_type='bcrypt',
                                to_type='secure_bcrypt',
                                success=True,
                                details=user_context
                            )
                    except Exception as e:
                        self.logger.error(f"Failed to migrate bcrypt hash for user {user_id}: {str(e)}")
                
                return result
            
            # Try legacy formats if enabled
            if self.enable_legacy_migration and self.legacy_handler.is_legacy_hash(hash_str):
                result = self.legacy_handler.verify_legacy_hash(password, hash_str)
                
                # Log legacy authentication attempt
                hash_type = self.legacy_handler.detect_hash_type(hash_str) or 'unknown'
                if self.log_security_events:
                    self.security_monitor.log_authentication_attempt(
                        user=user_id,
                        success=result,
                        details={
                            'hash_type': hash_type,
                            'verification_method': 'legacy_handler',
                            'ip_address': ip_address,
                            'requires_migration': result
                        }
                    )
                
                # If successful, migrate to secure format
                if result and user_context:
                    try:
                        new_hash = self.migrate_legacy_password(password, hash_str, user_context)
                        if new_hash:
                            user_context['new_hash'] = new_hash
                    except Exception as e:
                        self.logger.error(f"Failed to migrate legacy hash for user {user_id}: {str(e)}")
                
                return result
            
            # Unknown hash format
            self.logger.warning(f"Unknown hash format for user {user_id}: {hash_str[:10]}...")
            if self.log_security_events:
                self.security_monitor.log_authentication_attempt(
                    user=user_id,
                    success=False,
                    details={
                        'hash_type': 'unknown',
                        'verification_method': 'unknown',
                        'ip_address': ip_address,
                        'error_message': 'Unknown hash format'
                    }
                )
            
            return False
            
        except Exception as e:
            # Log security error
            if self.log_security_events:
                self.security_monitor.log_security_error(e, {
                    'operation': 'password_verification',
                    'user': user_context.get('user_id', 'unknown') if user_context else 'unknown',
                    'hash_type': 'unknown'
                })
            
            self.logger.error(f"Password verification error: {str(e)}")
            return False
    
    def validate_password_strength(self, password: str, user: Optional[Any] = None) -> ValidationResult:
        """
        Validate password strength with comprehensive checking.
        
        Args:
            password: Password to validate
            user: Optional user object for similarity checking
            
        Returns:
            ValidationResult: Complete validation result
            
        Requirements: 2.1, 2.2, 2.3, 2.4, 2.5 - Password strength validation
        """
        try:
            result = self.validator.validate(password, user)
            
            # Log validation attempt (without sensitive data)
            if self.log_security_events:
                user_id = getattr(user, 'id', 'unknown') if user else 'unknown'
                self.security_monitor.log_authentication_attempt(
                    user=user_id,
                    success=result.is_valid,
                    details={
                        'operation': 'password_validation',
                        'strength_score': result.strength_score,
                        'strength_level': result.strength_level,
                        'error_count': len(result.errors),
                        'warning_count': len(result.warnings)
                    }
                )
            
            return result
            
        except Exception as e:
            # Log validation error
            if self.log_security_events:
                self.security_monitor.log_security_error(e, {
                    'operation': 'password_validation',
                    'user': getattr(user, 'id', 'unknown') if user else 'unknown'
                })
            
            self.logger.error(f"Password validation error: {str(e)}")
            
            # Return failed validation result
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                strength_score=0,
                strength_level="weak",
                suggestions=["Please try again or contact support"]
            )
    
    def migrate_legacy_password(self, password: str, legacy_hash: str, 
                              user_context: Optional[Dict] = None) -> Optional[str]:
        """
        Migrate legacy password to secure format with comprehensive logging.
        
        Args:
            password: Plain text password
            legacy_hash: Legacy hash string
            user_context: Optional user context for logging
            
        Returns:
            Optional[str]: New secure hash if migration successful, None otherwise
            
        Requirements: 3.1, 3.3 - Legacy password migration with audit trail
        """
        try:
            if not self.enable_legacy_migration:
                self.logger.warning("Legacy password migration is disabled")
                return None
            
            # Use legacy handler for migration
            new_hash = self.legacy_handler.migrate_to_secure_hash(password, legacy_hash, user_context)
            
            if new_hash:
                user_id = user_context.get('user_id', 'unknown') if user_context else 'unknown'
                legacy_type = self.legacy_handler.detect_hash_type(legacy_hash) or 'unknown'
                
                # Log successful migration
                if self.log_security_events:
                    self.security_monitor.log_password_migration(
                        user=user_id,
                        from_type=legacy_type,
                        to_type='secure_bcrypt',
                        success=True,
                        details=user_context
                    )
                
                self.logger.info(f"Legacy password migration successful for user {user_id}: {legacy_type} -> secure_bcrypt")
            
            return new_hash
            
        except Exception as e:
            # Log migration error
            if self.log_security_events:
                self.security_monitor.log_security_error(e, {
                    'operation': 'legacy_password_migration',
                    'user': user_context.get('user_id', 'unknown') if user_context else 'unknown'
                })
            
            self.logger.error(f"Legacy password migration failed: {str(e)}")
            return None
    
    def handle_authentication_error(self, error: Exception, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Handle authentication errors with comprehensive error handling and recovery mechanisms.
        
        Args:
            error: Exception that occurred during authentication
            user_context: Optional user context for logging and recovery
            
        Returns:
            Dict[str, Any]: Error response with recovery instructions
            
        Requirements: 4.1, 4.2, 4.3, 4.4 - Error handling and recovery
        """
        try:
            user_id = user_context.get('user_id', 'unknown') if user_context else 'unknown'
            error_handler = get_error_handler()
            
            # Determine the type of error and handle appropriately
            error_message = str(error).lower()
            
            if isinstance(error, HashCorruptionError):
                # Already a comprehensive error, just create response
                return error_handler.create_recovery_response(error, for_admin=False)
            elif isinstance(error, LegacyPasswordError):
                # Already a comprehensive error, just create response
                return error_handler.create_recovery_response(error, for_admin=False)
            elif isinstance(error, ValidationError):
                # Already a comprehensive error, just create response
                return error_handler.create_recovery_response(error, for_admin=False)
            elif isinstance(error, AuthenticationError):
                # Already a comprehensive error, just create response
                return error_handler.create_recovery_response(error, for_admin=False)
            elif 'salt' in error_message or 'hash corruption' in error_message:
                # Handle hash corruption
                hash_error = error_handler.handle_hash_corruption(
                    error=error,
                    hash_sample=None,  # Don't expose hash in context
                    user_context=user_context
                )
                return error_handler.create_recovery_response(hash_error, for_admin=False)
            elif 'legacy' in error_message:
                # Handle legacy password error
                legacy_error = error_handler.handle_legacy_password_error(
                    error=error,
                    legacy_type='unknown',
                    operation='authentication',
                    user_context=user_context
                )
                return error_handler.create_recovery_response(legacy_error, for_admin=False)
            elif 'validation' in error_message:
                # Handle validation error - create a basic validation result
                validation_result = ValidationResult(
                    is_valid=False,
                    errors=[str(error)],
                    warnings=[],
                    strength_score=0,
                    strength_level="weak",
                    suggestions=["Please check your password and try again"]
                )
                validation_error = error_handler.handle_validation_error(
                    validation_result=validation_result,
                    user_context=user_context
                )
                return error_handler.create_recovery_response(validation_error, for_admin=False)
            else:
                # Handle general authentication error
                auth_error = error_handler.handle_authentication_error(
                    error=error,
                    failure_reason=str(error),
                    attempt_count=user_context.get('attempt_count', 1) if user_context else 1,
                    user_context=user_context
                )
                return error_handler.create_recovery_response(auth_error, for_admin=False)
                
        except Exception as e:
            # Fallback error handling if comprehensive error handling fails
            self.logger.error(f"Error in comprehensive authentication error handler: {str(e)}")
            
            # Create a basic safe response
            return {
                'success': False,
                'error_code': 'SYSTEM_ERROR',
                'message': 'A system error occurred. Please contact support.',
                'user_message': 'A system error occurred. Please contact support for assistance.',
                'admin_message': f'System error in authentication error handler: {str(e)}',
                'requires_password_reset': False,
                'timestamp': datetime.now().isoformat(),
                'error_id': str(uuid.uuid4()),
                'support_contact': 'Please contact support immediately.',
                'recovery_guidance': {
                    'immediate_action': 'Contact support',
                    'steps': [
                        'Contact technical support',
                        'Provide the error ID for faster resolution',
                        'Try again later'
                    ],
                    'support_available': True
                }
            }
            response.update({
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'error_type': error_type,
                'support_contact': 'Please contact support if this issue persists.'
            })
            
            self.logger.warning(f"Authentication error handled for user {user_id}: {error_code}", extra=response)
            return response
            
        except Exception as e:
            # Fallback error handling
            self.logger.error(f"Error in authentication error handler: {str(e)}")
            return {
                'success': False,
                'error_code': 'SYSTEM_ERROR',
                'message': 'System error occurred. Please contact support.',
                'user_message': 'A system error occurred. Please contact support for assistance.',
                'admin_message': f'System error in authentication error handler: {str(e)}',
                'requires_password_reset': False,
                'timestamp': datetime.now().isoformat(),
                'support_contact': 'Please contact support immediately.'
            }
    
    def get_security_report(self, timeframe_days: int = 7) -> SecurityReport:
        """
        Generate security report for monitoring and compliance.
        
        Args:
            timeframe_days: Number of days to include in report
            
        Returns:
            SecurityReport: Comprehensive security analysis
            
        Requirements: 6.4 - Security reporting functionality
        """
        try:
            timeframe = timedelta(days=timeframe_days)
            report = self.security_monitor.generate_security_report(timeframe)
            
            self.logger.info(f"Security report generated: {report.report_id}")
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating security report: {str(e)}")
            # Return empty report on error
            return SecurityReport(
                report_id=f"error_report_{int(datetime.now().timestamp())}",
                generated_at=datetime.now(),
                timeframe_start=datetime.now() - timedelta(days=timeframe_days),
                timeframe_end=datetime.now(),
                total_events=0,
                events_by_type={},
                events_by_severity={},
                brute_force_attempts=0,
                password_migrations=0,
                failed_authentications=0,
                successful_authentications=0,
                unique_users=0,
                unique_ips=0,
                top_failure_reasons=[],
                security_recommendations=["Error generating report - check system logs"]
            )
    
    def check_password_needs_update(self, hash_str: str) -> bool:
        """
        Check if password hash needs updating due to security requirements.
        
        Args:
            hash_str: Password hash to check
            
        Returns:
            bool: True if hash should be updated
        """
        try:
            # Check if it's a legacy hash that needs migration
            if self.legacy_handler.is_legacy_hash(hash_str):
                return True
            
            # Check if secure bcrypt hash needs updating
            if hash_str.startswith('secure_bcrypt$'):
                return self.hasher.must_update(hash_str)
            
            # Other bcrypt formats should be migrated to secure_bcrypt
            if NodeJSCompatiblePasswordHasher.is_bcrypt_hash(hash_str) or hash_str.startswith('bcrypt$'):
                return True
            
            # Unknown format should be updated
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking password update requirement: {str(e)}")
            return True  # Default to requiring update on error
    
    def get_password_hash_info(self, hash_str: str) -> Dict[str, Any]:
        """
        Get information about a password hash for administrative purposes.
        
        Args:
            hash_str: Password hash to analyze
            
        Returns:
            Dict[str, Any]: Hash information (safe for display)
        """
        try:
            if hash_str.startswith('secure_bcrypt$'):
                return self.hasher.safe_summary(hash_str)
            elif NodeJSCompatiblePasswordHasher.is_bcrypt_hash(hash_str):
                return {
                    'algorithm': 'bcrypt_nodejs',
                    'hash': mask_hash(hash_str),
                    'needs_migration': True
                }
            elif hash_str.startswith('bcrypt$'):
                return {
                    'algorithm': 'bcrypt_django',
                    'hash': mask_hash(hash_str),
                    'needs_migration': True
                }
            elif self.legacy_handler.is_legacy_hash(hash_str):
                hash_type = self.legacy_handler.detect_hash_type(hash_str)
                return {
                    'algorithm': f'legacy_{hash_type}',
                    'hash': mask_hash(hash_str),
                    'needs_migration': True,
                    'legacy_type': hash_type
                }
            else:
                return {
                    'algorithm': 'unknown',
                    'hash': mask_hash(hash_str),
                    'needs_migration': True,
                    'warning': 'Unknown hash format'
                }
                
        except Exception as e:
            self.logger.error(f"Error getting hash info: {str(e)}")
            return {
                'algorithm': 'error',
                'hash': '[error]',
                'needs_migration': True,
                'error': str(e)
            }


# Global password security controller instance
_password_security_controller = None

def get_password_security_controller() -> PasswordSecurityController:
    """
    Get global password security controller instance (singleton pattern).
    
    Returns:
        PasswordSecurityController: Global controller instance
    """
    global _password_security_controller
    if _password_security_controller is None:
        _password_security_controller = PasswordSecurityController()
    return _password_security_controller


class SecureAuthenticationBackend:
    """
    Django authentication backend that integrates with the PasswordSecurityController.
    
    This backend provides:
    - Enhanced password verification with legacy support
    - Automatic password migration during authentication
    - Comprehensive security logging and monitoring
    - Error handling and recovery mechanisms
    - Seamless Django admin compatibility
    
    Requirements addressed: 5.1, 5.2, 5.3, 5.4
    """
    
    def __init__(self):
        """Initialize the authentication backend."""
        self.controller = get_password_security_controller()
        self.logger = logging.getLogger('security.auth_backend')
        
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user with enhanced security features.
        
        Args:
            request: Django request object
            username: Username or email
            password: Plain text password
            **kwargs: Additional authentication parameters
            
        Returns:
            User object if authentication successful, None otherwise
        """
        try:
            if username is None or password is None:
                return None
            
            # Import User model
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Get user context for logging
            user_context = self._get_user_context(request, username)
            
            # Try to find user by username or email
            user = None
            try:
                # Try username first
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                try:
                    # Try email if username lookup fails
                    user = User.objects.get(email=username)
                except User.DoesNotExist:
                    # Log failed user lookup
                    self.controller.security_monitor.log_authentication_attempt(
                        user=username,
                        success=False,
                        details={
                            **user_context,
                            'error_message': 'User not found',
                            'lookup_method': 'username_and_email'
                        }
                    )
                    return None
            
            # Update user context with actual user ID
            user_context['user_id'] = str(user.id)
            user_context['username'] = user.username
            
            # Verify password using controller
            verification_result = self.controller.verify_password(
                password=password,
                hash_str=user.password,
                user_context=user_context
            )
            
            if verification_result:
                # Check if password was migrated
                if 'new_hash' in user_context:
                    # Update user's password hash
                    try:
                        user.password = user_context['new_hash']
                        user.save(update_fields=['password'])
                        
                        self.logger.info(f"Password hash updated for user {user.id} after successful migration")
                    except Exception as e:
                        self.logger.error(f"Failed to save migrated password for user {user.id}: {str(e)}")
                
                # Log successful authentication
                self.controller.security_monitor.log_authentication_attempt(
                    user=str(user.id),
                    success=True,
                    details={
                        **user_context,
                        'auth_backend': 'SecureAuthenticationBackend',
                        'password_migrated': 'new_hash' in user_context
                    }
                )
                
                return user
            else:
                # Log failed authentication
                self.controller.security_monitor.log_authentication_attempt(
                    user=str(user.id),
                    success=False,
                    details={
                        **user_context,
                        'error_message': 'Password verification failed',
                        'auth_backend': 'SecureAuthenticationBackend'
                    }
                )
                
                return None
                
        except Exception as e:
            # Handle authentication errors
            error_response = self.controller.handle_authentication_error(e, user_context)
            
            self.logger.error(f"Authentication error: {error_response.get('error_code', 'UNKNOWN')}")
            return None
    
    def get_user(self, user_id):
        """
        Get user by ID for Django authentication system.
        
        Args:
            user_id: User ID
            
        Returns:
            User object if found, None otherwise
        """
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
        except Exception as e:
            self.logger.error(f"Error getting user {user_id}: {str(e)}")
            return None
    
    def _get_user_context(self, request, username: str) -> Dict[str, Any]:
        """
        Extract user context from request for logging and security monitoring.
        
        Args:
            request: Django request object
            username: Username being authenticated
            
        Returns:
            Dict[str, Any]: User context dictionary
        """
        context = {
            'username': username,
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown') if request else 'Unknown',
            'session_id': request.session.session_key if request and hasattr(request, 'session') else None,
            'request_path': request.path if request else None,
            'auth_method': 'password',
            'timestamp': datetime.now().isoformat()
        }
        
        return context
    
    def _get_client_ip(self, request) -> Optional[str]:
        """
        Get client IP address from request.
        
        Args:
            request: Django request object
            
        Returns:
            Optional[str]: Client IP address
        """
        if not request:
            return None
            
        # Check for IP in various headers (for proxy/load balancer setups)
        ip_headers = [
            'HTTP_X_FORWARDED_FOR',
            'HTTP_X_REAL_IP',
            'HTTP_CF_CONNECTING_IP',  # Cloudflare
            'REMOTE_ADDR'
        ]
        
        for header in ip_headers:
            ip = request.META.get(header)
            if ip:
                # Handle comma-separated IPs (X-Forwarded-For can have multiple IPs)
                if ',' in ip:
                    ip = ip.split(',')[0].strip()
                
                # Basic IP validation
                if self._is_valid_ip(ip):
                    return ip
        
        return None
    
    def _is_valid_ip(self, ip: str) -> bool:
        """
        Basic IP address validation.
        
        Args:
            ip: IP address string
            
        Returns:
            bool: True if IP appears valid
        """
        try:
            import ipaddress
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False


# ============================================================================
# PERFORMANCE OPTIMIZATION UTILITIES
# ============================================================================

def initialize_password_security_performance():
    """
    Initialize all performance optimization components for password security.
    
    This function should be called during Django startup to ensure all
    performance components are properly initialized and configured.
    
    Requirements addressed: 7.1, 7.2, 7.3, 7.4
    """
    try:
        from .performance import optimize_password_operations
        
        # Initialize performance optimizations
        optimize_password_operations()
        
        # Initialize global components
        get_performance_monitor()
        get_password_validation_cache()
        get_concurrent_hash_processor()
        get_db_connection_manager()
        get_security_monitor()
        
        logger.info("Password security performance optimizations initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize password security performance optimizations: {str(e)}")


def get_password_security_performance_stats() -> Dict[str, Any]:
    """
    Get comprehensive performance statistics for password security operations.
    
    Returns:
        Dict[str, Any]: Performance statistics across all components
        
    Requirements addressed: 7.4 - Performance monitoring and metrics
    """
    try:
        from .performance import get_performance_summary
        return get_performance_summary()
        
    except Exception as e:
        logger.error(f"Failed to get performance statistics: {str(e)}")
        return {
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }


# Initialize performance optimizations on module import
try:
    initialize_password_security_performance()
except Exception as e:
    logger.warning(f"Performance optimization initialization failed: {str(e)}")


# Legacy compatibility functions with performance optimizations
@performance_tracked('legacy.hash_password')
def hash_password_optimized(password, rounds=12):
    """
    Hash password using bcrypt with performance optimizations
    
    Args:
        password (str): Plain text password
        rounds (int): Number of salt rounds
        
    Returns:
        str: Bcrypt hash string
    """
    processor = get_concurrent_hash_processor()
    return processor.process_hash_operation(
        NodeJSCompatiblePasswordHasher.hash_password, 
        password, 
        rounds
    )


@performance_tracked('legacy.verify_password_optimized')
def verify_password_optimized(password, hash_str):
    """
    Verify password against hash with enhanced legacy support, security monitoring, and performance optimizations
    
    Args:
        password (str): Plain text password
        hash_str (str): Hash string (bcrypt or legacy)
        
    Returns:
        bool: True if password matches
    """
    return verify_password(password, hash_str)