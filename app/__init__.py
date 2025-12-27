from flask import Flask, render_template, request, jsonify, session, g
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import os

load_dotenv()

# ✅ COMPLETE MULTI-LANGUAGE SUPPORT
LANGUAGES = {
    'en': {
        'Patta Application': 'Patta Application',
        'Google Satellite - House-level precision for land boundaries': 'Google Satellite - House-level precision for land boundaries',
        'Set Location': 'Set Location',
        'Get Precise Location': 'Get Precise Location',
        'Or search address...': 'Or search address...',
        'Google Satellite': 'Google Satellite',
        'Property Details': 'Property Details',
        'District': 'District',
        'Taluk': 'Taluk',
        'Village': 'Village',
        'Latitude': 'Latitude',
        'Longitude': 'Longitude',
        'Center Map': 'Center Map',
        'Application Details': 'Application Details',
        'Survey Number': 'Survey Number',
        'Subdivision': 'Subdivision',
        'Documents': 'Documents',
        'Submit Patta Application': 'Submit Patta Application',
        'Ready': 'Ready',
        'Loading...': 'Loading...',
        'Staff Dashboard': 'Staff Dashboard',
        'Manage Patta Applications - State-wise Analytics': 'Manage Patta Applications - State-wise Analytics',
        'Application Statistics': 'Application Statistics',
        'Total Applications': 'Total Applications',
        'Pending': 'Pending',
        'Approved': 'Approved',
        'Rejected': 'Rejected',
        'By State': 'By State',
        'State': 'State',
        'Total': 'Total',
        'Pending Applications': 'Pending Applications',
        'Ref ID': 'Ref ID',
        'Survey No.': 'Survey No.',
        'Location': 'Location',
        'Date': 'Date',
        'Status': 'Status',
        'Actions': 'Actions',
        'View': 'View',
        'Approve': 'Approve',
        'Reject': 'Reject',
        'Approve application': 'Approve application',
        'Approved!': 'Approved!',
        'Approval failed': 'Approval failed',
        'Rejection reason (optional):': 'Rejection reason (optional):',
        'Reject application': 'Reject application',
        'Rejected!': 'Rejected!',
        'Rejection failed': 'Rejection failed',
        'Reference:': 'Reference:',
        'Survey:': 'Survey:',
        'Lat/Lng:': 'Lat/Lng:',
        'Boundary:': 'Boundary:',
        'Admin Dashboard': 'Admin Dashboard',
        'Full system overview and management': 'Full system overview and management',
        'Total Users': 'Total Users',
        'Active Sessions': 'Active Sessions',
        'Security Events': 'Security Events',
        'Uptime': 'Uptime',
        'Citizen Dashboard - Patta Application': 'Citizen Dashboard - Patta Application',
        'Staff Dashboard - Patta Approvals': 'Staff Dashboard - Patta Approvals',
        'Secure Dashboard': 'Secure Dashboard',
        'Logout': 'Logout'
    },
    'ta': {
        'Patta Application': 'பட்டா விண்ணப்பம்',
        'Google Satellite - House-level precision for land boundaries': 'கூகுள் சதிலைட் - நில எல்லைகளுக்கான வீட்டு-நிலை துல்லியம்',
        'Set Location': 'இடத்தை அமைக்கவும்',
        'Get Precise Location': 'துல்லியமான இடத்தைப் பெறவும்',
        'Or search address...': 'அல்லது முகவர்ஷி தேடவும்...',
        'Google Satellite': 'கூகுள் சதிலைட்',
        'Property Details': 'அமைவு விவரங்கள்',
        'District': 'மாவட்டம்',
        'Taluk': 'தாசில்',
        'Village': 'கிராமம்',
        'Latitude': 'அக்ஷரேகை',
        'Longitude': 'தீர்க்கரேகை',
        'Center Map': 'வரைபடத்தை மையப்படுத்தவும்',
        'Application Details': 'விண்ணப்ப விவரங்கள்',
        'Survey Number': 'அளவு எண்',
        'Subdivision': 'பிரிவு',
        'Documents': 'ஆவணங்கள்',
        'Submit Patta Application': 'பட்டா விண்ணப்பத்தை சமர்ப்பிக்கவும்',
        'Ready': 'தயார்',
        'Loading...': 'ஏற்றுகிறது...',
        'Staff Dashboard': 'ஊழியர் டாஷ்போர்டு',
        'Manage Patta Applications - State-wise Analytics': 'பட்டா விண்ணப்பங்களை மாநில வாரியாக நிர்வகிக்கவும்',
        'Application Statistics': 'விண்ணப்ப புள்ளிவிவரங்கள்',
        'Total Applications': 'மொத்த விண்ணப்பங்கள்',
        'Pending': 'நிலுவையில்',
        'Approved': 'அங்கீகரிக்கப்பட்டது',
        'Rejected': 'நிராகரிக்கப்பட்டது',
        'By State': 'மாநில வாரியாக',
        'State': 'மாநிலம்',
        'Total': 'மொத்தம்',
        'Pending Applications': 'நிலுவையிலுள்ள விண்ணப்பங்கள்',
        'Ref ID': 'குறிப்பு ID',
        'Survey No.': 'அளவு எண்.',
        'Location': 'இடம்',
        'Date': 'தேதி',
        'Status': 'நிலை',
        'Actions': 'செயல்கள்',
        'View': 'பார்க்க',
        'Approve': 'அங்கீகரிக்க',
        'Reject': 'நிராகரி',
        'Approve application': 'விண்ணப்பத்தை அங்கீகரிக்கவும்',
        'Approved!': 'அங்கீகரிக்கப்பட்டது!',
        'Approval failed': 'அங்கீகரிப்பு தோல்வி',
        'Rejection reason (optional):': 'நிராகரிப்பு காரணம் (விரும்பினால்):',
        'Reject application': 'விண்ணப்பத்தை நிராகரிக்கவும்',
        'Rejected!': 'நிராகரிக்கப்பட்டது!',
        'Rejection failed': 'நிராகரிப்பு தோல்வி',
        'Reference:': 'குறிப்பு:',
        'Survey:': 'அளவு:',
        'Lat/Lng:': 'அக்ஷரேகை/தீர்க்கரேகை:',
        'Boundary:': 'எல்லை:',
        'Admin Dashboard': 'நிர்வாக டாஷ்போர்டு',
        'Full system overview and management': 'முழு அமைப்பு கண்ணோட்டம் மற்றும் நிர்வாகம்',
        'Total Users': 'மொத்த பயனர்கள்',
        'Active Sessions': 'செயல்படும் அமர்வுகள்',
        'Security Events': 'பாதுகாப்பு நிகழ்வுகள்',
        'Uptime': 'இணைப்பு நேரம்',
        'Citizen Dashboard - Patta Application': 'குடிமகன் டாஷ்போர்டு - பட்டா விண்ணப்பம்',
        'Staff Dashboard - Patta Approvals': 'ஊழியர் டாஷ்போர்டு - பட்டா அங்கீகாரங்கள்',
        'Secure Dashboard': 'பாதுகாப்பான டாஷ்போர்டு',
        'Logout': 'வெளியேறு'
    },
    'kn': {'Patta Application': 'ಪಟ್ಟಾ ಅರ್ಜಿ', 'District': 'ಜಿಲ್ಲೆ', 'Taluk': 'ತಾಲೂಕು', 'Village': 'ಗ್ರಾಮ', 'Survey Number': 'ಸರ್ವೇ ಸಂಖ್ಯೆ', 'Ready': 'ಸಿದ್ಧ', 'Pending': 'ಬಾಕಿ', 'Approved': 'ಒಪ್ಪಿದ', 'Rejected': 'ನಿರಾಕರಿಸಲಾಯಿತು', 'Staff Dashboard': 'ಸಿಬ್ಬೆಂದಿ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್'},
    'te': {'Patta Application': 'పట్టా అప్లికేషన్', 'District': 'జిల్లా', 'Taluk': 'తాలూకా', 'Village': 'గ్రామం', 'Survey Number': 'సర్వే నంబర్', 'Pending': 'పెండింగ్', 'Approved': 'అప్రూవ్ అయింది', 'Rejected': 'రిజెక్ట్ అయింది'},
    'hi': {'Patta Application': 'पट्टा आवेदन', 'District': 'जिला', 'Taluk': 'तहसील', 'Village': 'गांव', 'Survey Number': 'सर्वे नंबर', 'Pending': 'लंबित', 'Approved': 'अनुमोदित', 'Rejected': 'अस्वीकृत'},
    'ml': {'Patta Application': 'പട്ട ക്രമീകരണം', 'District': 'ജില്ല', 'Taluk': 'താലൂക്ക്', 'Village': 'ഗ്രാമം', 'Survey Number': 'സർവേ നമ്പർ', 'Pending': 'പെൻഡിങ്', 'Approved': 'അംഗീകരിച്ചു', 'Rejected': 'നിരസിച്ചു'},
    'bn': {'Patta Application': 'পট্টা আবেদন', 'District': 'জেলা', 'Taluk': 'থানা', 'Village': 'গ্রাম', 'Survey Number': 'সার্ভে নম্বর', 'Pending': 'বাধবে', 'Approved': 'অনুমোদিত', 'Rejected': 'প্রত্যাখ্যাত'}
}

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-prod')
    app.config['SESSION_TYPE'] = 'filesystem'

    # Firebase
    if not firebase_admin._apps:
        cred = credentials.Certificate(os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH'))
        firebase_admin.initialize_app(cred, {'projectId': os.getenv('FIREBASE_PROJECT_ID')})
    app.db = firestore.client()

    # ✅ LANGUAGE CONTEXT PROCESSOR
    @app.context_processor
    def inject_language():
        lang = request.cookies.get('lang', 'en')
        if lang not in LANGUAGES: lang = 'en'
        return dict(lang=LANGUAGES[lang], current_lang=lang)

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
        return render_template('index.html', **inject_language())

    @app.route('/dashboard')
    def dashboard():
        token = request.headers.get('Authorization', '').replace('Bearer ', '') or session.get('token')
        if not token: return render_template('index.html', **inject_language())
        try:
            uid = token
            user_doc = app.db.collection('users').document(uid).get()
            if not user_doc.exists: return render_template('index.html', **inject_language())
            user_data = user_doc.to_dict()
            role = user_data.get('role', 'citizen')
            if role == 'citizen': return render_template('citizen.html', **inject_language())
            elif role == 'staff': return render_template('staff.html', **inject_language())
            elif role == 'admin': return render_template('admin.html', **inject_language())
            else: return render_template('index.html', **inject_language())
        except Exception: return render_template('index.html', **inject_language())

    # ✅ BULLETPROOF CSP + GPS + IP GEOLOCATION
    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(self), microphone=(), camera=()'
        
        csp = ("default-src 'self'; "
               "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdnjs.cloudflare.com https://ipapi.co; "
               "style-src 'self' 'unsafe-inline' https://unpkg.com https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
               "font-src 'self' https://fonts.gstatic.com data:; "
               "img-src 'self' data: https: blob:; "
               "connect-src 'self' https://nominatim.openstreetmap.org https://tile.openstreetmap.org https://*.google.com https://ipapi.co; "
               "frame-ancestors 'none';")
        response.headers['Content-Security-Policy'] = csp
        return response

    return app
