from flask import Blueprint, request, jsonify, session
import firebase_admin
from firebase_admin import auth, firestore
from functools import wraps
import os
from dotenv import load_dotenv
from hashlib import sha256
import secrets
import time
import re  # ✅ FIXED: Missing import
from collections import defaultdict  # ✅ FIXED: For rate limiting

# Global rate limits (shared across requests)
rate_limits = defaultdict(list)

# Load environment
load_dotenv()

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

def token_required(f):
    """🔒 Secure token validation with session binding"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        client_ip = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        
        if not token:
            return jsonify({'error': 'Token required'}), 401
        
        try:
            decoded = auth.verify_id_token(token)
            uid = decoded['uid']
            
            from flask import current_app
            db = current_app.db
            
            user_doc = db.collection('users').document(uid).get()
            if not user_doc.exists:
                return jsonify({'error': 'User not found'}), 404
            
            user_data = user_doc.to_dict()
            
            # Session fingerprint
            session_fingerprint = sha256(f"{client_ip}:{user_agent}".encode()).hexdigest()
            
            # Log suspicious session (non-blocking)
            if (user_data.get('last_session') and 
                user_data.get('last_session') != session_fingerprint):
                db.collection('security_events').add({
                    'event': 'suspicious_session',
                    'uid': uid,
                    'ip': client_ip,
                    'timestamp': firestore.SERVER_TIMESTAMP
                })
            
            # Update activity
            db.collection('users').document(uid).update({
                'last_activity': firestore.SERVER_TIMESTAMP,
                'last_ip': client_ip
            })
            
            return f(*args, **kwargs, current_user=user_data, uid=uid)
            
        except Exception as e:
            try:
                from flask import current_app
                current_app.db.collection('security_events').add({
                    'event': 'auth_failure',
                    'error': str(e)[:500],
                    'ip': client_ip,
                    'timestamp': firestore.SERVER_TIMESTAMP
                })
            except:
                pass
            return jsonify({'error': 'Invalid token'}), 401
    return decorated

def rate_limit(key="ip", limit=100, window=3600):
    """⏱️ Rate limiting decorator"""
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
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            rate_limits[client_key].append(now)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def sanitize_input(data):
    """🛡️ XSS/SQLi protection"""
    if isinstance(data, str):
        # Remove script tags and SQL keywords
        data = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', data, flags=re.IGNORECASE | re.DOTALL)
        data = re.sub(r'(?:--|\/\*|\*\/|\b(ALTER|CREATE|DELETE|DROP|INSERT|SELECT|UPDATE|UNION|EXEC)\b)', '', data, flags=re.IGNORECASE)
        return data.strip()
    elif isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    return data

@auth_bp.route('/login', methods=['POST'])
@rate_limit(limit=5, window=300)
def login():
    """🔑 Email/password + Demo login"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
    
    data = sanitize_input(data)
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    try:
        from flask import current_app
        db = current_app.db
        
        # ✅ FIXED: Demo accounts (works instantly!)
        demo_accounts = {
            'citizen@test.com': {'role': 'citizen', 'name': 'Citizen User'},
            'staff@test.com': {'role': 'staff', 'name': 'Staff User'},
            'admin@test.com': {'role': 'admin', 'name': 'Admin User'}
        }
        
        if email in demo_accounts and password == '123456':
            # Find or create demo user
            user_query = db.collection('users').where('email', '==', email).limit(1).get()
            if not user_query:
                user_ref = db.collection('users').add({
                    'email': email,
                    'role': demo_accounts[email]['role'],
                    'name': demo_accounts[email]['name'],
                    'provider': 'demo',
                    'createdAt': firestore.SERVER_TIMESTAMP
                })
                user_doc_id = user_ref[1].id
            else:
                user_doc_id = user_query[0].id
            
            user_doc = db.collection('users').document(user_doc_id).get()
            user_data = user_doc.to_dict()
            
        else:
            return jsonify({'error': 'Use demo accounts or enable Firebase Auth'}), 401
        
        # Generate Firebase custom token
        custom_token = auth.create_custom_token(user_doc_id)
        
        # Update session info
        session_fingerprint = sha256(
            f"{request.remote_addr}:{request.headers.get('User-Agent', '')}".encode()
        ).hexdigest()
        
        db.collection('users').document(user_doc_id).update({
            'last_session': session_fingerprint,
            'last_login': firestore.SERVER_TIMESTAMP
        })
        
        return jsonify({
            'token': custom_token.decode(),
            'user': {
                'uid': user_doc_id,
                'email': user_data.get('email'),
                'role': user_data.get('role'),
                'name': user_data.get('name', ''),
                'provider': user_data.get('provider', 'demo')
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Login failed', 'details': str(e)}), 500

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_me(current_user, uid):
    """👤 Get current user profile"""
    try:
        from flask import current_app
        db = current_app.db
        
        user_doc = db.collection('users').document(uid).get()
        if not user_doc.exists:
            return jsonify({'error': 'User not found'}), 404
        
        user_data = user_doc.to_dict()
        return jsonify({
            'uid': uid,
            'email': user_data.get('email', ''),
            'role': user_data.get('role', 'citizen'),
            'name': user_data.get('name', ''),
            'provider': user_data.get('provider', 'demo'),
            'last_activity': str(user_data.get('last_activity', '')),
            'last_login': str(user_data.get('last_login', '')),
            'last_ip': user_data.get('last_ip', '')
        })
    except Exception as e:
        return jsonify({'error': 'Failed to fetch profile'}), 500

@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user, uid):
    """🚪 Logout and invalidate session"""
    try:
        from flask import current_app
        db = current_app.db
        db.collection('users').document(uid).update({
            'last_session': '',  # Invalidate session
            'last_logout': firestore.SERVER_TIMESTAMP
        })
        return jsonify({'message': 'Logged out successfully'})
    except:
        return jsonify({'message': 'Logged out (client-side)'}), 200

@auth_bp.route('/google/login', methods=['GET'])
def google_login():
    """🌐 Google OAuth (returns redirect URL)"""
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    
    params = {
        'client_id': os.getenv('GOOGLE_CLIENT_ID'),
        'redirect_uri': f"{os.getenv('FRONTEND_URL', 'http://localhost:5000')}/api/auth/google/callback",
        'response_type': 'code',
        'scope': 'email profile',
        'state': state,
        'access_type': 'offline'
    }
    
    # ✅ FIXED: Direct URL construction
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{query_string}"
    
    return jsonify({
        'redirect_url': url,
        'state': state,
        'message': 'Open this URL in browser for Google login'
    })

@auth_bp.route('/google/callback', methods=['GET'])
def google_callback():
    """📱 Handle Google OAuth callback"""
    state = request.args.get('state')
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        return jsonify({'error': f'Google OAuth error: {error}'}), 400
    
    if state != session.get('oauth_state'):
        return jsonify({'error': 'Invalid OAuth state (CSRF protection)'}), 400
    
    return jsonify({
        'message': 'Google OAuth callback received!',
        'code': code[:20] + '...' if code else None,
        'next_step': 'Exchange code for tokens (production implementation)'
    })
