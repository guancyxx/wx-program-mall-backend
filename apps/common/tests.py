"""
Tests for health endpoint functionality.
Validates Requirements: 1.1, 1.3, 1.4, 2.1, 2.2

Task 3.1: Test the health endpoint functionality
- Verify `/health/` endpoint returns HTTP 200 with valid JSON
- Test database connectivity reporting
- Ensure endpoint works without authentication
"""

import json
import time
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.db import connection, DatabaseError
from django.utils import timezone


class HealthEndpointTest(TestCase):
    """Test health endpoint functionality according to requirements."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
        self.health_url = '/health/'
    
    def test_health_endpoint_returns_200_with_valid_json(self):
        """
        Test that /health/ endpoint returns HTTP 200 with valid JSON.
        Validates: Requirements 1.1, 1.3
        """
        response = self.client.get(self.health_url)
        
        # Verify HTTP 200 status
        self.assertEqual(response.status_code, 200, 
                        "Health endpoint should return HTTP 200")
        
        # Verify response is valid JSON
        try:
            data = json.loads(response.content)
        except json.JSONDecodeError:
            self.fail("Health endpoint should return valid JSON")
        
        # Verify required JSON fields are present
        required_fields = ['status', 'timestamp', 'version', 'database', 'response_time_ms']
        for field in required_fields:
            self.assertIn(field, data, f"Health response should include '{field}' field")
        
        # Verify status is 'healthy' when database is working
        self.assertEqual(data['status'], 'healthy', 
                        "Health status should be 'healthy' when database is accessible")
        
        # Verify timestamp format
        try:
            timezone.datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        except ValueError:
            self.fail("Timestamp should be in valid ISO format")
        
        # Verify response time is a number
        self.assertIsInstance(data['response_time_ms'], (int, float),
                            "Response time should be a number")
        self.assertGreaterEqual(data['response_time_ms'], 0,
                              "Response time should be non-negative")
    
    def test_health_endpoint_response_time_requirement(self):
        """
        Test that health endpoint responds within 500ms.
        Validates: Requirements 1.2
        """
        start_time = time.time()
        response = self.client.get(self.health_url)
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(response_time_ms, 500, 
                       "Health endpoint should respond within 500ms")
    
    def test_health_endpoint_no_authentication_required(self):
        """
        Test that health endpoint works without authentication.
        Validates: Requirements 1.4
        """
        # Test without any authentication headers
        response = self.client.get(self.health_url)
        self.assertEqual(response.status_code, 200,
                        "Health endpoint should work without authentication")
        
        # Test with invalid authentication headers (should still work)
        response = self.client.get(self.health_url, 
                                 HTTP_AUTHORIZATION='Bearer invalid_token')
        self.assertEqual(response.status_code, 200,
                        "Health endpoint should work with invalid authentication")
        
        # Verify response contains valid health data
        data = json.loads(response.content)
        self.assertIn('status', data)
        self.assertIn('database', data)
    
    def test_database_connectivity_reporting_healthy(self):
        """
        Test database connectivity reporting when database is healthy.
        Validates: Requirements 2.1, 2.2
        """
        response = self.client.get(self.health_url)
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        
        # Verify database section exists
        self.assertIn('database', data, "Response should include database status")
        
        db_status = data['database']
        self.assertIsInstance(db_status, dict, "Database status should be a dictionary")
        
        # Verify database status fields
        self.assertIn('status', db_status, "Database status should include 'status' field")
        self.assertIn('message', db_status, "Database status should include 'message' field")
        
        # When database is healthy
        self.assertEqual(db_status['status'], 'healthy',
                        "Database status should be 'healthy' when accessible")
        self.assertEqual(db_status['message'], 'Database connection successful',
                        "Database message should indicate successful connection")
        
        # Overall status should be healthy
        self.assertEqual(data['status'], 'healthy',
                        "Overall status should be 'healthy' when database is healthy")
    
    @patch('apps.common.health_views.connection')
    def test_database_connectivity_reporting_unhealthy(self, mock_connection):
        """
        Test database connectivity reporting when database connection fails.
        Validates: Requirements 2.3
        """
        # Mock database connection failure
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = DatabaseError("Connection failed")
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        
        mock_connection.cursor.return_value = mock_cursor_context
        
        response = self.client.get(self.health_url)
        
        # Should return HTTP 503 when database is unhealthy
        self.assertEqual(response.status_code, 503,
                        "Health endpoint should return HTTP 503 when database fails")
        
        data = json.loads(response.content)
        
        # Verify overall status is unhealthy
        self.assertEqual(data['status'], 'unhealthy',
                        "Overall status should be 'unhealthy' when database fails")
        
        # Verify database status details
        db_status = data['database']
        self.assertEqual(db_status['status'], 'unhealthy',
                        "Database status should be 'unhealthy' when connection fails")
        self.assertEqual(db_status['message'], 'Database connection failed',
                        "Database message should indicate connection failure")
        self.assertIn('error', db_status,
                     "Database status should include error field when unhealthy")
    
    @patch('apps.common.health_views.connection')
    def test_database_health_check_performs_simple_query(self, mock_connection):
        """
        Test that database health check performs a simple query.
        Validates: Requirements 2.4
        """
        # Mock successful database query
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_connection.cursor.return_value = mock_cursor_context
        
        response = self.client.get(self.health_url)
        
        # Verify the simple query was executed
        mock_cursor.execute.assert_called_once_with("SELECT 1")
        mock_cursor.fetchone.assert_called_once()
        
        # Verify successful response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['database']['status'], 'healthy')
    
    def test_health_endpoint_json_response_structure(self):
        """
        Test that health endpoint returns properly structured JSON response.
        Validates: Requirements 1.3
        """
        response = self.client.get(self.health_url)
        self.assertEqual(response.status_code, 200)
        
        # Verify content type is JSON
        self.assertEqual(response['Content-Type'], 'application/json',
                        "Health endpoint should return JSON content type")
        
        data = json.loads(response.content)
        
        # Verify response structure matches expected format
        expected_structure = {
            'status': str,
            'timestamp': str,
            'version': str,
            'database': dict,
            'response_time_ms': (int, float)
        }
        
        for field, expected_type in expected_structure.items():
            self.assertIn(field, data, f"Response should include '{field}' field")
            self.assertIsInstance(data[field], expected_type,
                                f"Field '{field}' should be of type {expected_type}")
        
        # Verify database sub-structure
        db_data = data['database']
        db_required_fields = ['status', 'message']
        for field in db_required_fields:
            self.assertIn(field, db_data, 
                         f"Database status should include '{field}' field")