import re
import time
from collections import defaultdict
from functools import wraps
from flask import request, abort, jsonify, session, g
from cryptography.fernet import Fernet
import os
import base64
from hashlib import sha256
import secrets
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory rate limiting
rate_limits = defaultdict(list)
failed_logins = defaultdict(list)

def rate_limit(key_type="ip", limit=100, window=3600):
    """Enhanced rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_key = request.remote_addr if key_type == "ip" else key_type
            now = time.time()
            
            # Clean expired requests
            rate_limits[client_key] = [
                req_time for req_time in rate_limits[client_key] 
                if now - req_time < window
            ]
            
            if len(rate_limits[client_key]) >= limit:
                logger.warning(f"Rate limit exceeded for {client_key}")
                response = jsonify({'error': 'Too many requests. Try again later.'})
                response.status_code = 429
                response.headers['Retry-After'] = str(window)
                return response
            
            rate_limits[client_key].append(now)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# OWASP input sanitization
XSS_PATTERN = re.compile(
    r'<(?:script|img|svg|iframe|object|embed|frameset|frame|form|input|textarea|style|link)[^>]*?>|'
    r'on(?:abort|blur|change|click|dblclick|error|focus|load|mouse|submit|unload)=|'
    r'javascript:|vbscript:|data:',
    re.IGNORECASE | re.DOTALL
)

SQLI_PATTERN = re.compile(
    r'(?:--|\/\*|\*\/|@@|;|\b(ALTER|CREATE|DELETE|DROP|EXEC|INSERT|MERGE|SELECT|UPDATE|UNION|EXECUTE|DECLARE|WAITFOR)\b)',
    re.IGNORECASE
)

def sanitize_input(data):
    """Sanitize ALL inputs recursively"""
    if data is None:
        return None
    
    if isinstance(data, str):
        data = XSS_PATTERN.sub('', data)
        data = SQLI_PATTERN.sub('', data)
        data = data[:10000]
        data = data.strip().encode('utf-8', 'ignore').decode('utf-8')
        return data
    
    elif isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    
    elif isinstance(data, (int, float, bool)):
        return data
    
    return str(data)

# FIXED CSP (no invalid [] syntax)
CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdnjs.cloudflare.com https://ipapi.co; "
    "style-src 'self' 'unsafe-inline' https://unpkg.com https://cdnjs.cloudflare.com https://fonts.googleapis.com https://cdn.tailwindcss.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: https: blob: https://*.tile.openstreetmap.org https://*.googleusercontent.com https://lh3.googleusercontent.com; "
    "connect-src 'self' https://nominatim.openstreetmap.org https://tile.openstreetmap.org https://*.googleapis.com https://*.google.com https://ipapi.co; "
    "frame-src 'self' https://*.google.com; "
    "frame-ancestors 'none';"
)

def apply_security_headers(response):
    """Apply production security headers"""
    if isinstance(response, dict):
        response = jsonify(response)
    
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    response.headers['Content-Security-Policy'] = CSP
    response.headers['Permissions-Policy'] = 'geolocation=(self), microphone=(), camera=(), payment=()'
    
    return response

# Encryption
def get_encryption_suite():
    key_env = os.getenv('ENCRYPTION_KEY')
    if key_env:
        try:
            key = base64.urlsafe_b64decode(key_env)
            return Fernet(key)
        except:
            pass
    key = Fernet.generate_key()
    print("⚠️  Add to .env: ENCRYPTION_KEY=" + key.decode())
    return Fernet(key)

def encrypt_field(data):
    try:
        suite = get_encryption_suite()
        return suite.encrypt(str(data).encode()).decode()
    except:
        return sha256(str(data).encode()).hexdigest()[:32]

# CSRF Protection
def generate_csrf_token():
    token = secrets.token_urlsafe(32)
    if 'csrf_token' not in session:
        session['csrf_token'] = token
    return token

def validate_csrf_token(required=True):
    client_token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
    session_token = session.get('csrf_token')
    
    if required and (not client_token or not secrets.compare_digest(client_token, session_token)):
        logger.warning(f"CSRF validation failed from {request.remote_addr}")
        abort(403, "Invalid CSRF token")
    return True

# Session fingerprinting
def generate_session_fingerprint():
    user_agent = request.headers.get('User-Agent', '')[:500]
    ip = request.remote_addr
    accept_lang = request.headers.get('Accept-Language', '')[:100]
    fingerprint = sha256(f"{ip}:{user_agent}:{accept_lang}".encode()).hexdigest()
    return fingerprint[:32]

def bind_session_to_device():
    fingerprint = generate_session_fingerprint()
    if 'device_fingerprint' not in session:
        session['device_fingerprint'] = fingerprint
    elif not secrets.compare_digest(session['device_fingerprint'], fingerprint):
        logger.warning(f"Device fingerprint mismatch from {request.remote_addr}")
        session.clear()
        abort(403, "Session security violation")

# FIXED SECURITY DECORATORS (no circular dependencies)
def require_csrf():
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            validate_csrf_token(required=True)
            return f(*args, **kwargs)
        return decorated
    return decorator

def secure_file_upload():
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if request.content_length and request.content_length > 50 * 1024 * 1024:
                abort(413, "File too large")
            for key in request.form:
                request.form[key] = sanitize_input(request.form[key])
            return f(*args, **kwargs)
        return decorated
    return decorator

def secure_route():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            bind_session_to_device()
            
            if request.method in ['POST', 'PUT', 'PATCH']:
                if request.form:
                    request.form = sanitize_input(dict(request.form))
                if request.json:
                    request.json = sanitize_input(request.json)
            
            response = f(*args, **kwargs)
            return apply_security_headers(response)
        return decorated_function
    return decorator

def require_role(required_role):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Simple token check - customize for your auth
            token = request.headers.get('Authorization', '').replace('Bearer ', '') or session.get('token')
            if not token:
                abort(401, "Authentication required")
            return f(*args, **kwargs)
        return decorated
    return decorator

def security_middleware(app):
    """Global security middleware"""
    @app.before_request
    def before_request():
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            validate_csrf_token()
    
    @app.after_request
    def after_request(response):
        return apply_security_headers(response)
    
    return app
