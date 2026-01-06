#!/usr/bin/env python
"""
Simple test script for health endpoint functionality.
"""
import os
import sys
import django
import json
from django.conf import settings
from django.test import Client

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mall_server.settings.test_sqlite')
django.setup()

def test_health_endpoint():
    """Test the health endpoint functionality."""
    client = Client()
    
    print("Testing Health Endpoint...")
    print("=" * 50)
    
    try:
        # Test basic health endpoint
        response = client.get('/health/')
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.get('Content-Type', 'Not set')}")
        
        # Parse JSON response
        try:
            data = json.loads(response.content.decode())
            print(f"Response JSON: {json.dumps(data, indent=2)}")
            
            # Verify required fields
            required_fields = ['status', 'timestamp', 'version', 'database', 'response_time_ms']
            missing_fields = []
            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"❌ Missing required fields: {missing_fields}")
            else:
                print("✅ All required fields present")
            
            # Check status
            if data.get('status') == 'healthy':
                print("✅ Health status is 'healthy'")
            else:
                print(f"❌ Health status is '{data.get('status')}' (expected 'healthy')")
            
            # Check database status
            db_status = data.get('database', {})
            if db_status.get('status') == 'healthy':
                print("✅ Database status is 'healthy'")
            else:
                print(f"❌ Database status is '{db_status.get('status')}' (expected 'healthy')")
            
            # Check response time
            response_time = data.get('response_time_ms', 0)
            if isinstance(response_time, (int, float)) and response_time >= 0:
                print(f"✅ Response time: {response_time}ms")
            else:
                print(f"❌ Invalid response time: {response_time}")
                
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON response: {e}")
            print(f"Raw response: {response.content.decode()}")
            
    except Exception as e:
        print(f"❌ Error testing health endpoint: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 50)
    print("Health endpoint test completed")

if __name__ == '__main__':
    test_health_endpoint()