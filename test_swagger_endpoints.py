#!/usr/bin/env python
"""
Swagger/OpenAPI Endpoint Testing Script

This script validates that all endpoints are properly configured for OpenAPI schema generation.
Run this after applying the Swagger fixes to ensure everything works correctly.

Usage:
    python test_swagger_endpoints.py

Prerequisites:
    1. Install dependencies: pip install -r requirements.txt
    2. Set up environment: cp .env.example .env (edit as needed)
    3. Run migrations: python manage.py migrate
"""

import os
import sys
import django
import requests
from django.conf import settings
from django.test import Client
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'p2p_lending_platform.settings')
django.setup()

User = get_user_model()


class SwaggerEndpointTester:
    """Test suite for validating Swagger/OpenAPI endpoints"""

    def __init__(self):
        self.client = APIClient()
        self.test_user = None
        self.auth_token = None

    def setup_test_data(self):
        """Create test user and authentication token"""
        print("🔧 Setting up test data...")

        # Create test user
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='BORROWER'
        )

        # Create auth token
        self.auth_token, created = Token.objects.get_or_create(user=self.test_user)
        print(f"✅ Created test user: {self.test_user.username}")

    def test_schema_generation(self):
        """Test that OpenAPI schema generates without errors"""
        print("\n📊 Testing OpenAPI Schema Generation...")

        try:
            response = self.client.get('/api/schema/')
            if response.status_code == 200:
                print("✅ Schema generation successful")
                return True
            else:
                print(f"❌ Schema generation failed with status {response.status_code}")
                print(f"Response: {response.content.decode()}")
                return False
        except Exception as e:
            print(f"❌ Schema generation error: {str(e)}")
            return False

    def test_swagger_ui(self):
        """Test that Swagger UI loads without errors"""
        print("\n🌐 Testing Swagger UI...")

        try:
            response = self.client.get('/api/swagger/')
            if response.status_code == 200:
                print("✅ Swagger UI loads successfully")
                return True
            else:
                print(f"❌ Swagger UI failed with status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Swagger UI error: {str(e)}")
            return False

    def test_endpoint_schemas(self):
        """Test all endpoints for proper schema configuration"""
        print("\n🔍 Testing Individual Endpoint Schemas...")

        # List of all endpoints to test
        endpoints = [
            # User endpoints
            {'method': 'POST', 'url': '/api/users/register/', 'auth': False},
            {'method': 'POST', 'url': '/api/users/login/', 'auth': False},
            {'method': 'GET', 'url': '/api/users/profile/', 'auth': True},
            {'method': 'PUT', 'url': '/api/users/profile/update/', 'auth': True},

            # Wallet endpoints
            {'method': 'GET', 'url': '/api/wallets/', 'auth': True},
            {'method': 'POST', 'url': '/api/wallets/deposit/', 'auth': True},
            {'method': 'POST', 'url': '/api/wallets/withdraw/', 'auth': True},
            {'method': 'GET', 'url': '/api/wallets/balance/', 'auth': True},
            {'method': 'GET', 'url': '/api/wallets/transactions/', 'auth': True},

            # Loan endpoints
            {'method': 'POST', 'url': '/api/loans/', 'auth': True},
            {'method': 'GET', 'url': '/api/loans/available/', 'auth': True},
            {'method': 'GET', 'url': '/api/loans/my-loans/', 'auth': True},
            {'method': 'GET', 'url': '/api/loans/1/', 'auth': True},
            {'method': 'POST', 'url': '/api/loans/1/offer/', 'auth': True},
            {'method': 'POST', 'url': '/api/loans/1/accept-offer/', 'auth': True},
            {'method': 'POST', 'url': '/api/loans/1/fund/', 'auth': True},
            {'method': 'POST', 'url': '/api/loans/1/pay/', 'auth': True},
            {'method': 'GET', 'url': '/api/loans/1/schedule/', 'auth': True},
            {'method': 'GET', 'url': '/api/loans/pending-payments/', 'auth': True},
        ]

        success_count = 0
        total_count = len(endpoints)

        for endpoint in endpoints:
            success = self._test_single_endpoint(endpoint)
            if success:
                success_count += 1

        print(f"\n📈 Endpoint Schema Test Results: {success_count}/{total_count} passed")
        return success_count == total_count

    def _test_single_endpoint(self, endpoint):
        """Test a single endpoint for proper response"""
        method = endpoint['method']
        url = endpoint['url']
        requires_auth = endpoint['auth']

        # Set up authentication if required
        if requires_auth and self.auth_token:
            self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.auth_token.key}')
        else:
            self.client.credentials()

        try:
            if method == 'GET':
                response = self.client.get(url)
            elif method == 'POST':
                response = self.client.post(url, {})
            elif method == 'PUT':
                response = self.client.put(url, {})
            else:
                response = self.client.patch(url, {})

            # We expect 400/401/403 for most endpoints due to missing data/permissions
            # But NOT 500 (internal server error) which indicates schema issues
            if response.status_code < 500:
                print(f"✅ {method} {url} - Status: {response.status_code}")
                return True
            else:
                print(f"❌ {method} {url} - Server Error: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ {method} {url} - Exception: {str(e)}")
            return False

    def run_tests(self):
        """Run all tests and provide summary"""
        print("🚀 Starting Swagger/OpenAPI Endpoint Tests\n")

        # Setup test data
        self.setup_test_data()

        # Run tests
        tests = [
            self.test_schema_generation,
            self.test_swagger_ui,
            self.test_endpoint_schemas,
        ]

        results = []
        for test in tests:
            results.append(test())

        # Summary
        passed = sum(results)
        total = len(results)

        print(f"\n🎯 Test Summary: {passed}/{total} test suites passed")

        if passed == total:
            print("🎉 All tests passed! Swagger is working correctly.")
        else:
            print("⚠️  Some tests failed. Please check the errors above.")

        return passed == total


def run_curl_tests():
    """Alternative testing using curl commands"""
    print("\n🌐 cURL Test Commands (run these manually if server is running):")
    print("=" * 60)

    curl_commands = [
        "# Test schema generation",
        "curl -X GET http://localhost:8000/api/schema/",
        "",
        "# Test Swagger UI",
        "curl -X GET http://localhost:8000/api/swagger/",
        "",
        "# Test user registration",
        'curl -X POST http://localhost:8000/api/users/register/ \\',
        '  -H "Content-Type: application/json" \\',
        '  -d \'{"username": "testuser", "email": "test@example.com", "password": "testpass123", "role": "BORROWER"}\'',
        "",
        "# Test user login",
        'curl -X POST http://localhost:8000/api/users/login/ \\',
        '  -H "Content-Type: application/json" \\',
        '  -d \'{"username": "testuser", "password": "testpass123"}\'',
        "",
        "# Test wallet endpoints (requires auth token from login)",
        'curl -X GET http://localhost:8000/api/wallets/ \\',
        '  -H "Authorization: Token YOUR_TOKEN_HERE"',
    ]

    for cmd in curl_commands:
        print(cmd)


if __name__ == '__main__':
    try:
        tester = SwaggerEndpointTester()
        success = tester.run_tests()

        print("\n" + "=" * 60)
        run_curl_tests()

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"❌ Test setup failed: {str(e)}")
        print("\nMake sure you have:")
        print("1. Installed dependencies: pip install -r requirements.txt")
        print("2. Set up environment: cp .env.example .env")
        print("3. Run migrations: python manage.py migrate")
        sys.exit(1)
