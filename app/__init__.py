from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import os

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-prod')
    app.config['SESSION_TYPE'] = 'filesystem'
    
    # Firebase
    if not firebase_admin._apps:
        cred = credentials.Certificate(os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH'))
        firebase_admin.initialize_app(cred, {
            'projectId': os.getenv('FIREBASE_PROJECT_ID'),
        })
    app.db = firestore.client()
    
    # Blueprints
    from .auth import auth_bp
    from .patta import patta_bp
    from .admin import admin_bp
    from .chat import chat_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(patta_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(chat_bp)
    
    # 🔑 ROLE-BASED ROUTES
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/dashboard')
    def dashboard():
        token = request.headers.get('Authorization', '').replace('Bearer ', '') or session.get('token')
        if not token:
            return render_template('index.html')
        
        try:
            from firebase_admin import auth
            decoded = auth.verify_id_token(token)
            uid = decoded['uid']
            user_doc = app.db.collection('users').document(uid).get()
            if not user_doc.exists:
                return render_template('index.html')
            
            user_data = user_doc.to_dict()
            role = user_data.get('role', 'citizen')
            
            if role == 'citizen':
                return render_template('citizen.html')
            elif role == 'staff':
                return render_template('staff.html')
            elif role == 'admin':
                return render_template('admin.html')
            else:
                return render_template('index.html')
        except:
            return render_template('index.html')
    
    # Security
    from .security import apply_security_headers
    @app.after_request
    def security_headers(response):
        return apply_security_headers(response)
    
    return app
