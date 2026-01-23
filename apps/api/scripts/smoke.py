#!/usr/bin/env python3
"""
Smoke test script for Service Analytics API.
Checks critical endpoints after deployment.
"""
import sys
import os
import requests
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.settings import get_settings

settings = get_settings()

# Base URL for API (can be overridden by env)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "10"))


def check_endpoint(
    method: str,
    path: str,
    expected_status: int = 200,
    auth_token: Optional[str] = None,
    json_data: Optional[dict] = None,
    description: str = ""
) -> bool:
    """Check if an endpoint responds correctly."""
    url = f"{API_BASE_URL}{path}"
    headers = {}
    
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=API_TIMEOUT)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=json_data, timeout=API_TIMEOUT)
        else:
            print(f"❌ Unknown method: {method}")
            return False
        
        if response.status_code == expected_status:
            print(f"✅ {description or path}: {response.status_code}")
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
        check_endpoint("GET", "/health", description="Health check")
    )
    
    # 2. Shops endpoint (requires auth, but we check if it's accessible)
    # In production, you might want to skip this or use a test token
    auth_token = os.getenv("SMOKE_TEST_TOKEN")
    if auth_token:
        results.append(
            check_endpoint("GET", "/api/shops", auth_token=auth_token, description="GET /api/shops")
        )
        results.append(
            check_endpoint("GET", "/api/kpi/summary?period=30d", auth_token=auth_token, description="GET /api/kpi/summary")
        )
        results.append(
            check_endpoint("GET", "/api/extra-expenses?period=30d", auth_token=auth_token, description="GET /api/extra-expenses")
        )
    else:
        print("⚠️  SMOKE_TEST_TOKEN not set, skipping authenticated endpoints")
        print("   Set SMOKE_TEST_TOKEN env var to test authenticated endpoints")
    
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
