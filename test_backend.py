#!/usr/bin/env python3
"""Test script for Frankendash backend."""

import subprocess
import time
import requests
import json
import sys
import os
import secrets

def test_server_startup_without_password():
    """Test server refuses to start without DEMO_PASSWORD."""
    print("Testing server startup without DEMO_PASSWORD...")
    
    # Remove DEMO_PASSWORD from environment for this test
    env = os.environ.copy()
    if 'DEMO_PASSWORD' in env:
        del env['DEMO_PASSWORD']
    
    server_proc = subprocess.Popen(
        ['python3', 'server.py', '--port', '18081', '--host', '127.0.0.1'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )
    
    # Wait for process to exit
    time.sleep(1)
    return_code = server_proc.poll()
    
    if return_code is not None and return_code != 0:
        stderr = server_proc.stderr.read().decode('utf-8', errors='ignore')
        if 'DEMO_PASSWORD' in stderr and 'not set' in stderr.lower():
            print("✓ Server correctly refuses to start without DEMO_PASSWORD")
            return True
        else:
            print(f"✗ Server exited with code {return_code} but error message unclear")
            print(f"Stderr: {stderr[:200]}")
            return False
    else:
        print("✗ Server should have exited but is still running")
        server_proc.terminate()
        server_proc.wait()
        return False

def test_static_files():
    """Test static file serving."""
    print("\nTesting static file serving...")
    
    results = []
    
    # Test root endpoint
    try:
        response = requests.get('http://127.0.0.1:18080/', timeout=5)
        if response.status_code == 200 and 'text/html' in response.headers.get('Content-Type', ''):
            print("✓ GET / returns HTML")
            results.append(True)
        else:
            print(f"✗ GET /: HTTP {response.status_code}, Content-Type: {response.headers.get('Content-Type')}")
            results.append(False)
    except Exception as e:
        print(f"✗ GET /: {e}")
        results.append(False)
    
    # Test index.html
    try:
        response = requests.get('http://127.0.0.1:18080/index.html', timeout=5)
        if response.status_code == 200 and 'text/html' in response.headers.get('Content-Type', ''):
            print("✓ GET /index.html returns HTML")
            results.append(True)
        else:
            print(f"✗ GET /index.html: HTTP {response.status_code}")
            results.append(False)
    except Exception as e:
        print(f"✗ GET /index.html: {e}")
        results.append(False)
    
    # Test style.css
    try:
        response = requests.get('http://127.0.0.1:18080/style.css', timeout=5)
        if response.status_code == 200 and 'text/css' in response.headers.get('Content-Type', ''):
            print("✓ GET /style.css returns CSS")
            results.append(True)
        else:
            print(f"✗ GET /style.css: HTTP {response.status_code}")
            results.append(False)
    except Exception as e:
        print(f"✗ GET /style.css: {e}")
        results.append(False)
    
    return all(results)

def test_demo_login():
    """Test demo login endpoint."""
    print("\nTesting demo login...")
    
    results = []
    
    # Test with wrong password
    try:
        response = requests.post(
            'http://127.0.0.1:18080/api/demo-login',
            json={'password': 'wrong-password'},
            timeout=5
        )
        if response.status_code == 401:
            data = response.json()
            if data.get('ok') == False:
                print("✓ POST /api/demo-login with wrong password returns 401")
                results.append(True)
            else:
                print(f"✗ Wrong password test: expected ok=false, got {data}")
                results.append(False)
        else:
            print(f"✗ Wrong password test: expected 401, got {response.status_code}")
            results.append(False)
    except Exception as e:
        print(f"✗ Wrong password test: {e}")
        results.append(False)
    
    # Test with correct password
    try:
        demo_password = os.environ['DEMO_PASSWORD']  # set by test_backend(); no literal value
        response = requests.post(
            'http://127.0.0.1:18080/api/demo-login',
            json={'password': demo_password},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('ok') == True and 'Set-Cookie' in response.headers:
                print("✓ POST /api/demo-login with correct password returns 200 and cookie")
                results.append(True)
                # Return the session cookie for subsequent tests
                return all(results), response.headers.get('Set-Cookie')
            else:
                print(f"✗ Correct password test: expected ok=true with cookie, got {data}")
                results.append(False)
        else:
            print(f"✗ Correct password test: expected 200, got {response.status_code}")
            results.append(False)
    except Exception as e:
        print(f"✗ Correct password test: {e}")
        results.append(False)
    
    return all(results), None

def test_api_endpoints_with_auth(session_cookie):
    """Test API endpoints require authentication."""
    print("\nTesting API endpoints with authentication...")
    
    endpoints = [
        ('/api/health', 'Health check'),
        ('/api/phones', 'Phones data'),
        ('/api/gateway', 'Gateway data'),
        ('/api/notifications', 'Notifications data')
    ]
    
    results = []
    
    # Test without cookie (should get 401)
    for endpoint, description in endpoints:
        try:
            response = requests.get(f'http://127.0.0.1:18080{endpoint}', timeout=5)
            if response.status_code == 401:
                data = response.json()
                if data.get('ok') == False and 'Authentication' in data.get('error', ''):
                    print(f"✓ {description} without cookie returns 401")
                else:
                    print(f"✗ {description} without cookie: wrong error format")
                    results.append(False)
            else:
                print(f"✗ {description} without cookie: expected 401, got {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"✗ {description} without cookie: {e}")
            results.append(False)
    
    # Test with cookie (should get 200)
    headers = {'Cookie': session_cookie} if session_cookie else {}
    for endpoint, description in endpoints:
        try:
            response = requests.get(f'http://127.0.0.1:18080{endpoint}', 
                                  headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ {description} with cookie returns 200")
                results.append(True)
                
                # Special check for phones endpoint - should have B's data
                if endpoint == '/api/phones' and 'location_data' in data:
                    age = data['location_data'].get('age_hours', 0)
                    # Should be roughly 1 day old (from 2026-11-19), not ~433 hours
                    if age < 48 and age > 0.1:  # Reasonable range for 1-day old data
                        print(f"  ✓ Location age reflects B's 2026-11-19 file: {age:.1f}h")
                    else:
                        print(f"  ✗ Unexpected location age: {age:.1f}h (should be ~1 day)")
                        results.append(False)
            else:
                print(f"✗ {description} with cookie: expected 200, got {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"✗ {description} with cookie: {e}")
            results.append(False)
    
    return all(results)

def test_backend():
    """Test the backend server."""
    
    # Set test DEMO_PASSWORD
    os.environ['DEMO_PASSWORD'] = secrets.token_urlsafe(24)
    
    # Start server in background
    print("Starting Frankendash server on port 18080...")
    server_proc = subprocess.Popen(
        ['python3', 'server.py', '--port', '18080', '--host', '127.0.0.1'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Give server time to start
    time.sleep(2)
    
    all_results = []
    
    # Run tests
    all_results.append(test_server_startup_without_password())
    all_results.append(test_static_files())
    
    login_success, session_cookie = test_demo_login()
    all_results.append(login_success)
    
    if login_success and session_cookie:
        all_results.append(test_api_endpoints_with_auth(session_cookie))
    
    # Stop server
    server_proc.terminate()
    server_proc.wait()
    
    # Summary
    passed = sum(all_results)
    total = len(all_results)
    print(f"\nTest summary: {passed}/{total} test groups passed")
    
    # Clean up test password
    del os.environ['DEMO_PASSWORD']
    
    return all(all_results)

if __name__ == '__main__':
    if test_backend():
        print("\nBackend test PASSED")
        sys.exit(0)
    else:
        print("\nBackend test FAILED")
        sys.exit(1)
