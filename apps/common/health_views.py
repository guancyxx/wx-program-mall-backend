"""
Health check views for the mall server application.
Provides endpoints for monitoring application health and status.
"""
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from django.db import connection
import time
import logging

logger = logging.getLogger(__name__)


class BasicHealthCheckView(View):
    """
    Basic health check endpoint that returns HTTP 200 with JSON response.
    No authentication required for monitoring tools.
    Includes database connectivity verification.
    """
    
    def get(self, request):
        """
        Handle GET request to /health/ endpoint.
        Returns basic health status with timestamp and database connectivity.
        """
        start_time = time.time()
        
        # Basic health response structure
        health_response = {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'version': '1.0.0'
        }
        
        # Check database connectivity
        db_status, db_error = self._check_database_health()
        health_response['database'] = db_status
        
        # Determine overall status based on database health
        if db_status['status'] != 'healthy':
            health_response['status'] = 'unhealthy'
            # Log database connectivity issues
            logger.error(f"Database health check failed: {db_error}")
        
        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000
        health_response['response_time_ms'] = round(response_time_ms, 2)
        
        # Return appropriate HTTP status based on overall health
        status_code = 200 if health_response['status'] == 'healthy' else 503
        
        return JsonResponse(health_response, status=status_code)
    
    def _check_database_health(self):
        """
        Verify database connectivity using a simple SELECT query.
        
        Returns:
            tuple: (db_status_dict, error_message)
        """
        try:
            # Perform simple database connectivity check
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
            # If we get here, database is accessible
            if result and result[0] == 1:
                return {
                    'status': 'healthy',
                    'message': 'Database connection successful'
                }, None
            else:
                return {
                    'status': 'unhealthy',
                    'message': 'Database query returned unexpected result'
                }, 'Unexpected query result'
                
        except Exception as e:
            # Database connection failed
            error_message = str(e)
            return {
                'status': 'unhealthy',
                'message': 'Database connection failed',
                'error': 'Database connectivity error'  # Generic error for external consumption
            }, error_message