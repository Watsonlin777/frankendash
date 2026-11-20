#!/usr/bin/env python3
"""Test script for Frankendash backend."""

import subprocess
import time
import requests
import json
import sys

def test_backend():
    """Test the backend server."""
    
    # Start server in background
    print("Starting Frankendash server on port 18080...")
    server_proc = subprocess.Popen(
        ['python3', 'server.py', '--port', '18080', '--host', '127.0.0.1'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Give server time to start
    time.sleep(2)
    
    # Test endpoints
    endpoints = [
        ('/api/health', 'Health check'),
        ('/api/phones', 'Phones data'),
        ('/api/gateway', 'Gateway data'),
        ('/api/notifications', 'Notifications data')
    ]
    
    results = []
    for endpoint, description in endpoints:
        try:
            response = requests.get(f'http://127.0.0.1:18080{endpoint}', timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ {description}: OK (status: {data.get('status', 'N/A')})")
                results.append(True)
            else:
                print(f"✗ {description}: HTTP {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"✗ {description}: {e}")
            results.append(False)
    
    # Test root endpoint
    try:
        response = requests.get('http://127.0.0.1:18080/', timeout=5)
        if response.status_code == 200:
            print("✓ Root endpoint: OK")
            results.append(True)
        else:
            print(f"✗ Root endpoint: HTTP {response.status_code}")
            results.append(False)
    except Exception as e:
        print(f"✗ Root endpoint: {e}")
        results.append(False)
    
    # Stop server
    server_proc.terminate()
    server_proc.wait()
    
    # Summary
    print(f"\nTest summary: {sum(results)}/{len(results)} passed")
    return all(results)

if __name__ == '__main__':
    if test_backend():
        print("Backend test PASSED")
        sys.exit(0)
    else:
        print("Backend test FAILED")
        sys.exit(1)
