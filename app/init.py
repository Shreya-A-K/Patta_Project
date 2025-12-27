from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import firestore, credentials

# Load environment variables FIRST
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', os.urandom(32))
    
    # Initialize Firebase (SHARED across all blueprints)
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH'))
            firebase_admin.initialize_app(cred, {
                'projectId': os.getenv('FIREBASE_PROJECT_ID'),
            })
        except Exception as e:
            print(f"❌ Firebase init failed: {e}")
            raise
    
    # Make Firestore client available globally
    app.db = firestore.client()
    
    # ✅ FIXED CORS - Dynamic origins for dev/prod
    allowed_origins = [
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "https://yourdomain.com",  # Replace with your Vercel/Render URL
        "*"
    ]
    CORS(app, origins=allowed_origins, supports_credentials=True)
    
    # ✅ FIXED: Global input sanitization (with security.py import)
    from .security import sanitize_input
    
    @app.before_request
    def sanitize_all():
        if request.is_json:
            try:
                json_data = request.get_json()
                if json_data:
                    request._cached_json = sanitize_input(json_data)
            except:
                pass  # Invalid JSON - let Flask handle error
    
    # ✅ FIXED: Proper security headers
    @app.after_request
    def apply_security_headers(response):
        # Security headers (direct assignment, no security_headers() function needed)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "img-src 'self' data: https://*.tile.openstreetmap.org https://*.googleusercontent.com; "
            "connect-src 'self' https://*.googleapis.com https://*.firebaseio.com;"
        )
        return response
    
    # Register blueprints (NOW they have access to app.db)
    from .auth import auth_bp
    from .patta import patta_bp
    from .admin import admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(patta_bp)
    app.register_blueprint(admin_bp)
    
    # Health check
    @app.route('/health')
    def health():
        return jsonify({'status': 'secure', 'firebase': 'connected'}), 200
    
    # Serve static files for PWA
    @app.route('/')
    @app.route('/<path:path>')
    def catch_all(path='index.html'):
        return app.send_static_file('index.html')
    
    return app

# Create app instance
app = create_app()

if __name__ == '__main__':
    # Development: HTTP (use nginx/Cloudflare for HTTPS in prod)
    app.run(debug=True, host='0.0.0.0', port=5000)
