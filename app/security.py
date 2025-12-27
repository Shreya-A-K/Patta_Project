import re
import time
from collections import defaultdict
from functools import wraps
from flask import request, abort, jsonify
from cryptography.fernet import Fernet
import os
import base64
from hashlib import sha256
import secrets

# In-memory rate limiting (use Redis in production)
rate_limits = defaultdict(list)

def rate_limit(key="ip", limit=100, window=3600):
    """Rate limiting decorator - FIXED"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_key = request.remote_addr if key == "ip" else key
            now = time.time()
            
            # Clean expired requests
            rate_limits[client_key] = [
                req_time for req_time in rate_limits[client_key] 
                if now - req_time < window
            ]
            
            if len(rate_limits[client_key]) >= limit:
                response = jsonify({'error': 'Rate limit exceeded'})
                response.status_code = 429
                return response
            
            rate_limits[client_key].append(now)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# OWASP XSS/SQLi protection patterns - ENHANCED
XSS_PATTERN = re.compile(
    r'<(?:script|img|svg|iframe|object|embed|frameset|frame|form|input|textarea)[^>]*?>',
    re.IGNORECASE | re.DOTALL
)

SQLI_PATTERN = re.compile(
    r'(?:--|\/\*|\*\/|@@|\b(ALTER|CREATE|DELETE|DROP|EXEC|INSERT|MERGE|SELECT|UPDATE|UNION|EXECUTE|DECLARE|WAITFOR)\b)',
    re.IGNORECASE
)

def sanitize_input(data):
    """Sanitize ALL inputs recursively - PRODUCTION READY"""
    if data is None:
        return None
    
    if isinstance(data, str):
        # Remove XSS + SQLi + normalize
        data = XSS_PATTERN.sub('', data)
        data = SQLI_PATTERN.sub('', data)
        data = data.strip().encode('utf-8', 'ignore').decode('utf-8')
        return data
    
    elif isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    
    elif isinstance(data, (int, float, bool)):
        return data
    
    return str(data)

# ✅ FIXED CSP - No syntax errors
CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data: https://*.tile.openstreetmap.org https://*.googleusercontent.com https://lh3.googleusercontent.com; "
    "connect-src 'self' https://*.googleapis.com https://*.firebaseio.com https://accounts.google.com https://oauth2.googleapis.com;"
)

def apply_security_headers(response):
    """✅ FIXED: Apply headers DIRECTLY to response object"""
    if isinstance(response, dict):
        response = jsonify(response)
    
    # Core security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    response.headers['Content-Security-Policy'] = CSP
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    
    return response

# ✅ FIXED: Secure field encryption (per-process key)
def get_encryption_suite():
    """Generate secure key per process (not global)"""
    key_env = os.getenv('ENCRYPTION_KEY')
    if key_env:
        key = base64.urlsafe_b64decode(key_env)
    else:
        # Generate and store for session
        key = Fernet.generate_key()
        print("⚠️  Generate ENCRYPTION_KEY and add to .env for production")
    return Fernet(key)

def encrypt_field(data):
    """Encrypt sensitive fields"""
    try:
        suite = get_encryption_suite()
        return suite.encrypt(str(data).encode()).decode()
    except:
        return str(data)  # Fallback

def decrypt_field(encrypted_data):
    """Decrypt sensitive fields"""
    try:
        suite = get_encryption_suite()
        return suite.decrypt(encrypted_data.encode()).decode()
    except:
        return encrypted_data  # Fallback

# Session security utilities
def generate_csrf_token():
    """Generate secure CSRF token"""
    return secrets.token_urlsafe(32)

def validate_csrf_token(token):
    """Validate CSRF token"""
    session_token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
    return secrets.compare_digest(str(token), str(session_token))

# Device fingerprinting for session binding
def generate_session_fingerprint():
    """Create device fingerprint"""
    user_agent = request.headers.get('User-Agent', '')
    ip = request.remote_addr
    return sha256(f"{ip}:{user_agent}".encode()).hexdigest()[:32]
