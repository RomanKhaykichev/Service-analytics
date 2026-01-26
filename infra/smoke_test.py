#!/usr/bin/env python3
"""
Smoke test script for Service Analytics API.
Checks critical endpoints after deployment.

Usage:
    python infra/smoke_test.py
    # Or with custom base URL:
    API_BASE_URL=http://localhost:8000 python infra/smoke_test.py
"""
import sys
import os
import requests
from typing import Optional

# Base URL for API (can be overridden by env)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "10"))


def check_endpoint(
    method: str,
    path: str,
    expected_status: int = 200,
    auth_token: Optional[str] = None,
    user_id: Optional[str] = None,
    json_data: Optional[dict] = None,
    description: str = "",
    check_json: bool = False
) -> bool:
    """Check if an endpoint responds correctly."""
    url = f"{API_BASE_URL}{path}"
    headers = {}
    
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    elif user_id:
        # Use X-User-Id header for dev mode
        headers["X-User-Id"] = user_id
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=API_TIMEOUT)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=json_data, timeout=API_TIMEOUT)
        else:
            print(f"❌ Unknown method: {method}")
            return False
        
        if response.status_code == expected_status:
            status_msg = f"✅ {description or path}: {response.status_code}"
            if check_json:
                try:
                    data = response.json()
                    if isinstance(data, dict) and "ok" in data:
                        status_msg += f" (ok: {data.get('ok')})"
                    elif isinstance(data, list):
                        status_msg += f" (items: {len(data)})"
                    elif isinstance(data, dict) and "expenses" in data:
                        status_msg += f" (expenses: {len(data.get('expenses', []))})"
                except:
                    pass
            print(status_msg)
            return True
        else:
            print(f"❌ {description or path}: Expected {expected_status}, got {response.status_code}")
            if response.text:
                print(f"   Response: {response.text[:200]}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ {description or path}: Connection refused (API not running?)")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ {description or path}: Timeout after {API_TIMEOUT}s")
        return False
    except Exception as e:
        print(f"❌ {description or path}: {type(e).__name__}: {e}")
        return False


def main():
    """Run smoke tests."""
    print("=" * 60)
    print("Service Analytics API - Smoke Tests")
    print("=" * 60)
    print(f"API Base URL: {API_BASE_URL}")
    print()
    
    results = []
    
    # 1. Health check (no auth required)
    results.append(
        check_endpoint("GET", "/api/health", description="GET /api/health", check_json=True)
    )
    
    # 2. Test endpoints with auth (JWT token or X-User-Id for dev mode)
    auth_token = os.getenv("SMOKE_TEST_TOKEN")
    test_user_id = os.getenv("SMOKE_TEST_USER_ID", "00000000-0000-0000-0000-000000000001")
    
    if auth_token:
        # Use JWT token if provided
        user_id = None
        print(f"ℹ️  Using JWT token for authentication")
    else:
        # Use X-User-Id header for dev mode
        user_id = test_user_id
        print(f"ℹ️  Using X-User-Id header (dev mode): {user_id}")
    print()
    
    # Test endpoints
    if auth_token or user_id:
        results.append(
            check_endpoint("GET", "/api/shops", user_id=user_id, auth_token=auth_token, 
                          description="GET /api/shops", check_json=True)
        )
        results.append(
            check_endpoint("GET", "/api/kpi/summary?period=30d", user_id=user_id, auth_token=auth_token,
                          description="GET /api/kpi/summary?period=30d", check_json=True)
        )
        results.append(
            check_endpoint("GET", "/api/charts/revenue-daily?period=30d", user_id=user_id, auth_token=auth_token,
                          description="GET /api/charts/revenue-daily?period=30d", check_json=True)
        )
        results.append(
            check_endpoint("GET", "/api/extra-expenses?period=30d", user_id=user_id, auth_token=auth_token,
                          description="GET /api/extra-expenses?period=30d", check_json=True)
        )
    else:
        print("⚠️  No authentication method available")
        print("   Set SMOKE_TEST_TOKEN (JWT) or SMOKE_TEST_USER_ID (dev mode) env var")
    
    # Summary
    print()
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All smoke tests passed!")
        return 0
    else:
        print("❌ Some smoke tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
