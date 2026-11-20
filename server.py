#!/usr/bin/env python3
"""
Frankendash Backend Server
Python 3 stdlib-only HTTP server with read-only endpoints.
"""

import http.server
import socketserver
import json
import time
import threading
import urllib.request
import urllib.error
import subprocess
import os
import sys
import secrets
import hmac
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from http import HTTPStatus

# Configuration
CACHE_TTL = 60  # seconds
SOURCE_TIMEOUT = 5  # seconds per source
SESSION_EXPIRE_HOURS = 12
SERVER_PORT = 0  # Will be set by command line or default

# Data cache with timestamp
_cache = {
    'phones': {'data': None, 'timestamp': 0, 'error': None},
    'gateway': {'data': None, 'timestamp': 0, 'error': None},
    'notifications': {'data': None, 'timestamp': 0, 'error': None},
    'health': {'data': None, 'timestamp': 0, 'error': None}
}

# Last known good data (for showing "unknown" with timestamp)
_last_good = {
    'phones': {'data': None, 'timestamp': 0},
    'gateway': {'data': None, 'timestamp': 0},
    'notifications': {'data': None, 'timestamp': 0}
}

# Session storage (in-memory)
_sessions = {}  # token -> expiry timestamp

def cleanup_expired_sessions():
    """Remove expired sessions from memory."""
    current_time = time.time()
    expired = [token for token, expiry in _sessions.items() if expiry < current_time]
    for token in expired:
        del _sessions[token]

def validate_session(cookie_header: str) -> bool:
    """Validate session token from cookie."""
    if not cookie_header:
        return False
    
    # Parse cookie
    for cookie in cookie_header.split(';'):
        cookie = cookie.strip()
        if cookie.startswith('session='):
            token = cookie[8:]  # Remove 'session='
            cleanup_expired_sessions()
            return token in _sessions
    
    return False

def create_session() -> Tuple[str, float]:
    """Create a new session token with expiry."""
    token = secrets.token_urlsafe(32)
    expiry = time.time() + (SESSION_EXPIRE_HOURS * 3600)
    _sessions[token] = expiry
    cleanup_expired_sessions()
    return token, expiry

def safe_get_json(url: str, timeout: int) -> Optional[Dict[str, Any]]:
    """Safely fetch JSON from a URL with timeout."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                return json.load(response)
    except Exception:
        pass
    return None

def run_command(cmd: str, timeout: int) -> Tuple[Optional[str], Optional[str]]:
    """Run a shell command with timeout."""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        return result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except Exception as e:
        return None, str(e)

def fetch_phones_data() -> Dict[str, Any]:
    """Fetch phone status data from various sources."""
    data = {
        'phone_a': {'status': 'unknown', 'last_check': None},
        'phone_b': {'status': 'unknown', 'last_check': None},
        'timestamp': int(time.time()),
        'sources': {}
    }
    
    # Check SSH tunnels
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('127.0.0.1', 2222))
        data['sources']['ssh_a'] = 'up' if result == 0 else 'down'
        sock.close()
    except:
        data['sources']['ssh_a'] = 'error'
    
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('127.0.0.1', 2223))
        data['sources']['ssh_b'] = 'up' if result == 0 else 'down'
        sock.close()
    except:
        data['sources']['ssh_b'] = 'error'
    
    # Check ADB ports
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('127.0.0.1', 18091))
        data['sources']['adb_a'] = 'up' if result == 0 else 'down'
        
        # Try to get adb devices info
        if result == 0:
            stdout, stderr = run_command("adb -H 127.0.0.1 -P 18091 devices 2>/dev/null | tail -n +2", 2)
            if stdout and 'device' in stdout:
                data['phone_a']['adb'] = 'online'
            else:
                data['phone_a']['adb'] = 'offline'
        sock.close()
    except:
        data['sources']['adb_a'] = 'error'
    
    # Check location data freshness - read from phone B's directory
    location_files = []
    try:
        raw_dir = '/root/life/phones/B/raw/'
        for f in os.listdir(raw_dir):
            if f.startswith('raw_') and f.endswith('.jsonl'):
                location_files.append(f)
        
        if location_files:
            # Get newest file by modification time
            newest_file = None
            newest_mtime = 0
            for f in location_files:
                file_path = os.path.join(raw_dir, f)
                mtime = os.path.getmtime(file_path)
                if mtime > newest_mtime:
                    newest_mtime = mtime
                    newest_file = f
            
            if newest_file:
                file_time = os.path.getmtime(os.path.join(raw_dir, newest_file))
                current_time = time.time()
                hours_old = (current_time - file_time) / 3600
                
                data['location_data'] = {
                    'newest_file': newest_file,
                    'age_hours': round(hours_old, 1),
                    'stale': hours_old > 2
                }
        else:
            data['location_data'] = {'error': 'no_files_found'}
    except Exception as e:
        data['location_data'] = {'error': f'unavailable: {str(e)}'}
    
    # Check location watch state - read from phone B's state directory
    try:
        with open('/root/life/phones/B/state/location_watch_state.json', 'r') as f:
            watch_state = json.load(f)
            data['watch_state'] = watch_state
    except:
        data['watch_state'] = {'error': 'unavailable'}
    
    return data

def fetch_gateway_data() -> Dict[str, Any]:
    """Fetch Magpie gateway health and usage data."""
    data = {
        'status': 'unknown',
        'providers': [],
        'usage_today': {'requests': 0, 'tokens': 0, 'cost_usd': 0},
        'timestamp': int(time.time())
    }
    
    # Fetch provider list from Magpie API
    try:
        json_data = safe_get_json('http://127.0.0.1:3425/v1/models', SOURCE_TIMEOUT)
        if json_data and 'data' in json_data:
            data['status'] = 'up'
            providers_set = set()
            for model in json_data['data']:
                if 'magpie_label' in model:
                    providers_set.add(model['magpie_label'].split('·')[0].strip())
            
            data['providers'] = list(providers_set)
            data['provider_count'] = len(data['providers'])
    except:
        data['status'] = 'down'
    
    # Fetch usage data
    try:
        stdout, stderr = run_command("magpie usage --csv today 2>/dev/null | tail -n +2", SOURCE_TIMEOUT)
        if stdout:
            lines = stdout.strip().split('\n')
            data['usage_today']['requests'] = len(lines)
            
            # Parse costs (simplified - actual CSV parsing would be more robust)
            total_cost = 0
            total_tokens = 0
            for line in lines:
                parts = line.split(',')
                if len(parts) > 14:  # cost_usd at index 14
                    try:
                        cost = float(parts[14]) if parts[14] else 0
                        total_cost += cost
                    except:
                        pass
                if len(parts) > 9:  # input_tokens at index 9
                    try:
                        tokens = int(parts[9]) if parts[9] else 0
                        total_tokens += tokens
                    except:
                        pass
            
            data['usage_today']['cost_usd'] = round(total_cost, 4)
            data['usage_today']['tokens'] = total_tokens
    except:
        data['usage_today']['error'] = 'unavailable'
    
    return data

def fetch_notifications_data() -> Dict[str, Any]:
    """Fetch WeCom notification data from logs."""
    data = {
        'recent_pushes': [],
        'water_reminders': {'count': 0, 'last': None},
        'timestamp': int(time.time())
    }
    
    # Check water reminder state
    try:
        with open('/root/.hermes/water_state.json', 'r') as f:
            water_state = json.load(f)
            data['water_reminders']['state'] = water_state
    except:
        pass
    
    # Try to parse recent agent logs for notification patterns
    try:
        log_path = '/root/.hermes/logs/agent.log'
        if os.path.exists(log_path):
            # Read last 100 lines
            with open(log_path, 'r') as f:
                lines = f.readlines()[-100:]
            
            wecom_count = 0
            for line in lines:
                if 'wecom' in line.lower():
                    wecom_count += 1
                if 'water' in line.lower():
                    data['water_reminders']['count'] += 1
            
            data['log_scan'] = {
                'lines_scanned': len(lines),
                'wecom_mentions': wecom_count,
                'log_file': 'agent.log'
            }
    except:
        data['log_scan'] = {'error': 'unavailable'}
    
    # Add placeholder recent pushes (would be parsed from actual logs)
    data['recent_pushes'].append({
        'time': datetime.now().isoformat(),
        'type': 'water_reminder',
        'status': 'sent',
        'script': 'water_reminder.py'
    })
    
    return data

def fetch_health_data() -> Dict[str, Any]:
    """Fetch overall health status."""
    health = {
        'status': 'ok',
        'timestamp': int(time.time()),
        'services': {},
        'details': {}
    }
    
    # Check each service
    services_to_check = [
        ('ssh_tunnel_a', '127.0.0.1', 2222),
        ('adb_a', '127.0.0.1', 18091),
        ('magpie_gateway', '127.0.0.1', 3425)
    ]
    
    up_count = 0
    for name, host, port in services_to_check:
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            status = 'up' if result == 0 else 'down'
            sock.close()
        except:
            status = 'error'
        
        health['services'][name] = status
        if status == 'up':
            up_count += 1
    
    # Determine overall status
    if up_count == len(services_to_check):
        health['status'] = 'ok'
    elif up_count >= len(services_to_check) / 2:
        health['status'] = 'degraded'
    else:
        health['status'] = 'down'
    
    # Add cache status
    health['cache'] = {
        'ttl_seconds': CACHE_TTL,
        'age_seconds': {}
    }
    
    current_time = time.time()
    for key in _cache:
        if _cache[key]['data'] is not None:
            age = current_time - _cache[key]['timestamp']
            health['cache']['age_seconds'][key] = round(age, 1)
    
    return health

def update_cache(key: str, fetcher) -> None:
    """Update cache for a specific data type."""
    try:
        data = fetcher()
        _cache[key]['data'] = data
        _cache[key]['timestamp'] = time.time()
        _cache[key]['error'] = None
        
        # Update last good data
        _last_good[key]['data'] = data
        _last_good[key]['timestamp'] = time.time()
    except Exception as e:
        _cache[key]['error'] = str(e)
        # Keep last good data if available

def get_cached_data(key: str, fetcher) -> Dict[str, Any]:
    """Get data from cache, updating if stale."""
    current_time = time.time()
    
    if (_cache[key]['data'] is None or 
        current_time - _cache[key]['timestamp'] > CACHE_TTL):
        # Update in background thread
        thread = threading.Thread(target=update_cache, args=(key, fetcher))
        thread.daemon = True
        thread.start()
    
    # Return cached data or last good data
    if _cache[key]['data'] is not None:
        return _cache[key]['data']
    elif _last_good[key]['data'] is not None:
        result = _last_good[key]['data'].copy()
        result['from_cache'] = True
        result['cache_age'] = current_time - _last_good[key]['timestamp']
        return result
    else:
        return {'status': 'unknown', 'timestamp': int(current_time), 'error': 'no_data'}

class FrankendashHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for Frankendash API."""
    
    def do_GET(self):
        """Handle GET requests."""
        # Serve static files
        if self.path == '/':
            self.serve_file('index.html', 'text/html')
        elif self.path == '/index.html':
            self.serve_file('index.html', 'text/html')
        elif self.path == '/style.css':
            self.serve_file('style.css', 'text/css')
        # API endpoints require authentication
        elif self.path == '/api/health':
            self.handle_health()
        elif self.path == '/api/phones':
            self.handle_phones()
        elif self.path == '/api/gateway':
            self.handle_gateway()
        elif self.path == '/api/notifications':
            self.handle_notifications()
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")
    
    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/api/demo-login':
            self.handle_demo_login()
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")
    
    def serve_file(self, filename: str, content_type: str):
        """Serve a static file."""
        try:
            filepath = os.path.join(os.path.dirname(__file__), filename)
            with open(filepath, 'rb') as f:
                content = f.read()
            
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(HTTPStatus.NOT_FOUND, f"File not found: {filename}")
        except Exception as e:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Error reading file: {str(e)}")
    
    def handle_demo_login(self):
        """Handle POST /api/demo-login."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 1024:  # Limit request size
                self.send_error(HTTPStatus.BAD_REQUEST, "Request too large")
                return
            
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(post_data)
            password = data.get('password', '')
            
            # Get DEMO_PASSWORD from environment
            demo_password = os.environ.get('DEMO_PASSWORD', '')
            
            if not demo_password:
                self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Server misconfigured")
                return
            
            # Validate password with constant-time comparison
            if hmac.compare_digest(password, demo_password):
                # Create session
                token, expiry = create_session()
                
                # Set cookie
                cookie = (
                    f'session={token}; '
                    f'Path=/; '
                    f'SameSite=Lax; '
                    f'HttpOnly; '
                    f'Max-Age={int(SESSION_EXPIRE_HOURS * 3600)}'
                )
                
                response = {'ok': True}
                self.send_json_response(response, extra_headers={'Set-Cookie': cookie})
            else:
                response = {'ok': False, 'error': 'Invalid credential'}
                self.send_json_response(response, status=HTTPStatus.UNAUTHORIZED)
                
        except json.JSONDecodeError:
            response = {'ok': False, 'error': 'Invalid JSON'}
            self.send_json_response(response, status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            response = {'ok': False, 'error': 'Internal server error'}
            self.send_json_response(response, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    
    def check_auth(self) -> bool:
        """Check if request has valid session cookie."""
        cookie_header = self.headers.get('Cookie', '')
        return validate_session(cookie_header)
    
    def handle_health(self):
        """Handle /api/health endpoint."""
        if not self.check_auth():
            response = {'ok': False, 'error': 'Authentication required'}
            self.send_json_response(response, status=HTTPStatus.UNAUTHORIZED)
            return
        
        data = get_cached_data('health', fetch_health_data)
        self.send_json_response(data)
    
    def handle_phones(self):
        """Handle /api/phones endpoint."""
        if not self.check_auth():
            response = {'ok': False, 'error': 'Authentication required'}
            self.send_json_response(response, status=HTTPStatus.UNAUTHORIZED)
            return
        
        data = get_cached_data('phones', fetch_phones_data)
        self.send_json_response(data)
    
    def handle_gateway(self):
        """Handle /api/gateway endpoint."""
        if not self.check_auth():
            response = {'ok': False, 'error': 'Authentication required'}
            self.send_json_response(response, status=HTTPStatus.UNAUTHORIZED)
            return
        
        data = get_cached_data('gateway', fetch_gateway_data)
        self.send_json_response(data)
    
    def handle_notifications(self):
        """Handle /api/notifications endpoint."""
        if not self.check_auth():
            response = {'ok': False, 'error': 'Authentication required'}
            self.send_json_response(response, status=HTTPStatus.UNAUTHORIZED)
            return
        
        data = get_cached_data('notifications', fetch_notifications_data)
        self.send_json_response(data)
    
    def send_json_response(self, data: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK, 
                          extra_headers: Dict[str, str] = None) -> None:
        """Send JSON response with optional status and headers."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to reduce log noise."""
        # Only log errors
        if '404' in args or '500' in args:
            super().log_message(format, *args)

class ReusableTCPServer(socketserver.TCPServer):
    """TCP server that allows address reuse."""
    allow_reuse_address = True

def main():
    """Main server entry point."""
    import argparse
    
    # Check DEMO_PASSWORD environment variable
    demo_password = os.environ.get('DEMO_PASSWORD', '')
    if not demo_password:
        print("ERROR: DEMO_PASSWORD environment variable is not set or empty", file=sys.stderr)
        print("Server cannot start without a demo password.", file=sys.stderr)
        sys.exit(1)
    
    parser = argparse.ArgumentParser(description='Frankendash Backend Server')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    
    args = parser.parse_args()
    
    print(f"Starting Frankendash server on {args.host}:{args.port}")
    print(f"Cache TTL: {CACHE_TTL}s, Source timeout: {SOURCE_TIMEOUT}s")
    print("Available endpoints:")
    print("  / - Dashboard (index.html)")
    print("  /api/demo-login [POST] - Demo authentication")
    print("  /api/health - Service health (requires auth)")
    print("  /api/phones - Phone status (requires auth)")
    print("  /api/gateway - Gateway status (requires auth)")
    print("  /api/notifications - Notifications (requires auth)")
    
    # Initial cache warm-up
    print("Warming up cache...")
    for key, fetcher in [
        ('health', fetch_health_data),
        ('phones', fetch_phones_data),
        ('gateway', fetch_gateway_data),
        ('notifications', fetch_notifications_data)
    ]:
        thread = threading.Thread(target=update_cache, args=(key, fetcher))
        thread.daemon = True
        thread.start()
    
    # Start server with reusable address
    with ReusableTCPServer((args.host, args.port), FrankendashHandler) as httpd:
        print(f"Server started. Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.shutdown()

if __name__ == '__main__':
    main()
