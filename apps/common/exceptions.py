"""
Custom exception handlers for consistent API responses
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns consistent error responses
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Log the exception
        logger.error(f"API Exception: {exc}", exc_info=True)
        
        # Create custom error response format
        custom_response_data = {
            'code': response.status_code,
            'msg': 'An error occurred',
            'errors': response.data
        }

        # Handle specific error types
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            custom_response_data['msg'] = 'Validation error'
        elif response.status_code == status.HTTP_401_UNAUTHORIZED:
            custom_response_data['msg'] = 'Authentication required'
        elif response.status_code == status.HTTP_403_FORBIDDEN:
            custom_response_data['msg'] = 'Permission denied'
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            custom_response_data['msg'] = 'Resource not found'
        elif response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
            custom_response_data['msg'] = 'Method not allowed'
        elif response.status_code >= 500:
            custom_response_data['msg'] = 'Internal server error'
            # Don't expose internal errors in production
            if not hasattr(context['request'], 'user') or not context['request'].user.is_staff:
                custom_response_data['errors'] = {'detail': 'Internal server error'}

        response.data = custom_response_data

    return response