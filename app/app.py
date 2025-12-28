from flask import Flask, redirect, request, session, render_template, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime, timedelta
import google.generativeai as genai

# =========================
# GLOBAL VARIABLES
# =========================
applications = []
DATA_FILE = 'patta_data.json'
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', None)

# =========================
# DATA HELPERS
# =========================
def load_data():
    global applications
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                applications = data.get('applications', [])
            print(f"✅ Loaded {len(applications)} applications")
            return
        except Exception as e:
            print(f"❌ Load failed: {e}")

    # Test data if file doesn't exist
    applications.clear()
    applications.extend([
        {
            'ref_id': 'PATTA-20251228-0001',
            'citizen_email': 'citizen@test.com',
            'village': 'Guindy',
            'taluk': 'Velachery',
            'district': 'Chennai',
            'surveyNo': '123',
            'subdivNo': 'A/45',
            'status': 'pending',
            'submitted_at': datetime.now().isoformat(),
            'documents': {}
        },
        {
            'ref_id': 'PATTA-20251228-0002',
            'citizen_email': 'citizen2@test.com',
            'village': 'Anna Nagar',
            'taluk': 'Aminjikarai',
            'district': 'Chennai',
            'surveyNo': '456',
            'subdivNo': 'B/12',
            'status': 'approved',
            'submitted_at': (datetime.now() - timedelta(days=5)).isoformat(),
            'documents': {},
            'approved_by': {'name': 'Admin User', 'email': 'admin@test.com'}
        }
    ])
    print("✅ Test data loaded")

def save_data(app):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump({'applications': app.applications}, f, indent=2)
        print("💾 Data saved")
    except Exception as e:
        print(f"❌ Save failed: {e}")

# =========================
# APP FACTORY
# =========================
def create_app():
    app = Flask(__name__)
    app.secret_key = 'patta-super-secret-2025'

    # =========================
    # Attach global state
    # =========================
    app.applications = applications
    app.next_ref_id = 3

    # =========================
    # Gemini AI configuration
    # =========================
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        print("✅ Gemini AI ready")
    else:
        print("⚠️ GEMINI_API_KEY missing, AI disabled")

    # =========================
    # Uploads folder
    # =========================
    UPLOAD_FOLDER = 'uploads'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Load data
    load_data()

    # =========================
    # CONTEXT PROCESSORS
    # =========================
    @app.context_processor
    def inject_session():
        return dict(session=session)

    @app.context_processor
    def inject_language():
        lang = request.cookies.get('lang', 'en')
        languages = {
    'en': {
        'Patta Application': 'Patta Portal', 
        'Logout': 'Logout',
        'Track Applications': 'Track My Applications',
        'Track My Applications': 'Track My Applications',
        'Staff Dashboard - Patta Verification': 'Staff Dashboard - Patta Verification',
        'Patta Verification Dashboard': 'Patta Verification Dashboard'
    },
    'ta': {
        'Patta Application': 'பட்டா போர்டல்', 
        'Logout': 'வெளியேறு',
        'Track Applications': 'என் விண்ணப்பங்களைப் பின்தொடரவும்',
        'Track My Applications': 'என் விண்ணப்பங்களைப் பின்தொடரவும்',
        'Staff Dashboard - Patta Verification': 'பட்டா சரிபார்ப்பு டாஷ்போர்ட்',
        'Patta Verification Dashboard': 'பட்டா சரிபார்ப்பு டாஷ்போர்ட்'
    },
    'kn': {
        'Patta Application': 'ಪಟ್ಟಾ ಪೋರ್ಟಲ್',
        'Logout': 'ಬಿಡಾ',
        'Track Applications': 'ನನ್ನ ಅರ್ಜಿಗಳನ್ನು ಟ್ರ್ಯಾಕ್ ಮಾಡಿ',
        'Track My Applications': 'ನನ್ನ ಅರ್ಜಿಗಳನ್ನು ಟ್ರ್ಯಾಕ್ ಮಾಡಿ',
        'Staff Dashboard - Patta Verification': 'ಪಟ್ಟಾ ಪರಿಶೀಲನೆ ಸ್ಟಾಫ್ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್',
        'Patta Verification Dashboard': 'ಪಟ್ಟಾ ಪರಿಶೀಲನೆ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್'
    },
    'te': {
        'Patta Application': 'పట్టా పోర్టల్',
        'Logout': 'లాగౌట్',
        'Track Applications': 'నా అప్లికేషన్లను ట్రాక్ చేయండి',
        'Track My Applications': 'నా అప్లికేషన్లను ట్రాక్ చేయండి',
        'Staff Dashboard - Patta Verification': 'పట్టా ధృవీకరణ స్టాఫ్ డాష్‌బోర్డ్',
        'Patta Verification Dashboard': 'పట్టా ధృవీకరణ డాష్‌బోర్డ్'
    },
    'ml': {
        'Patta Application': 'പട്ട ഓർട്ടൽ',
        'Logout': 'ലോഗൗട്ട്',
        'Track Applications': 'എന്റെ അപേക്ഷകൾ ട്രാക്ക് ചെയ്യുക',
        'Track My Applications': 'എന്റെ അപേക്ഷകൾ ട്രാക്ക് ചെയ്യുക',
        'Staff Dashboard - Patta Verification': 'പട്ട സ്ഥിരീകരണ സ്റ്റാഫ് ഡാഷ്ബോർഡ്',
        'Patta Verification Dashboard': 'പട്ട സ്ഥിരീകരണ ഡാഷ്ബോർഡ്'
    },
    'hi': {
        'Patta Application': 'पट्टा पोर्टल',
        'Logout': 'लॉग आउट',
        'Track Applications': 'मेरे आवेदनों को ट्रैक करें',
        'Track My Applications': 'मेरे आवेदनों को ट्रैक करें',
        'Staff Dashboard - Patta Verification': 'पट्टा सत्यापन स्टाफ डैशबोर्ड',
        'Patta Verification Dashboard': 'पट्टा सत्यापन डैशबोर्ड'
    },
    'bn': {
        'Patta Application': 'পট্টা পোর্টাল',
        'Logout': 'লগ আউট',
        'Track Applications': 'আমার আবেদনগুলি ট্র্যাক করুন',
        'Track My Applications': 'আমার আবেদনগুলি ট্র্যাক করুন',
        'Staff Dashboard - Patta Verification': 'পট্টা যাচাই স্টাফ ড্যাশবোর্ড',
        'Patta Verification Dashboard': 'পট্টা যাচাই ড্যাশবোর্ড'
    },
    'mr': {
        'Patta Application': 'पट्टा पोर्टल',
        'Logout': 'बाहेर पडा',
        'Track Applications': 'माझ्या अर्जांचा मागोवा घ्या',
        'Track My Applications': 'माझ्या अर्जांचा मागोवा घ्या',
        'Staff Dashboard - Patta Verification': 'पट्टा तपासणी स्टाफ डॅशबोर्ड',
        'Patta Verification Dashboard': 'पट्टा तपासणी डॅशबोर्ड'
    },
    'gu': {
        'Patta Application': 'પટ્ટા પોર્ટલ',
        'Logout': 'લૉગઆઉટ',
        'Track Applications': 'મારા અરજીઓ ટ્રેક કરો',
        'Track My Applications': 'મારા અરજીઓ ટ્રેક કરો',
        'Staff Dashboard - Patta Verification': 'પટ્ટા ચકાસણી સ્ટાફ ડેશબોર્ડ',
        'Patta Verification Dashboard': 'પટ્ટા ચકાસણી ડેશબોર્ડ'
    },
    'pa': {
        'Patta Application': 'ਪਟਟਾ ਪੋਰਟਲ',
        'Logout': 'ਲੌਗ ਆਊਟ',
        'Track Applications': 'ਮੇਰੀਆਂ ਅਰਜ਼ੀਆਂ ਟਰੈਕ ਕਰੋ',
        'Track My Applications': 'ਮੇਰੀਆਂ ਅਰਜ਼ੀਆਂ ਟਰੈਕ ਕਰੋ',
        'Staff Dashboard - Patta Verification': 'ਪਟਟਾ ਜਾਂਚ ਸਟਾਫ਼ ਡੈਸ਼ਬੋਰਡ',
        'Patta Verification Dashboard': 'ਪਟਟਾ ਜਾਂਚ ਡੈਸ਼ਬੋਰਡ'
    }
}
        return dict(lang=languages.get(lang, languages['en']), current_lang=lang)

    # =========================
    # FILE SERVER
    # =========================
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        if '..' in filename or filename.startswith('/'):
            return "Access Denied", 403
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.isfile(path):
            return "File not found", 404
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # =========================
    # HOME & LOGIN
    # =========================
    @app.route('/', methods=['GET', 'POST'])
    def home():
        role = session.get('role')
        if role == 'admin': return redirect('/admin')
        if role == 'staff': return redirect('/staff')
        if role == 'citizen': return redirect('/citizen')
        return render_template('index.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'GET': return redirect('/') if session.get('role') else render_template('index.html')
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        users = {
            'citizen@test.com': {'password': '123456', 'role': 'citizen', 'name': 'Citizen User'},
            'staff@test.com': {'password': '123456', 'role': 'staff', 'name': 'Staff User'},
            'admin@test.com': {'password': '123456', 'role': 'admin', 'name': 'Admin User'}
        }
        user = users.get(email)
        if not user or user['password'] != password:
            return render_template('index.html', error='Invalid email or password')
        session['role'] = user['role']
        session['name'] = user['name']
        session['email'] = email
        if user['role'] == 'admin': return redirect('/admin')
        if user['role'] == 'staff': return redirect('/staff')
        return redirect('/citizen')

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect('/')

    # =========================
    # DASHBOARDS
    # =========================
    @app.route('/citizen')
    def citizen():
        if session.get('role') != 'citizen': return redirect('/')
        return render_template('citizen.html')

    @app.route('/staff')
    def staff():
        if session.get('role') not in ['staff', 'admin']: return redirect('/')
        return render_template('staff.html')

    @app.route('/admin')
    def admin():
        if session.get('role') != 'admin': return redirect('/')
        return render_template('admin.html')

    # =========================
    # ADMIN API
    # =========================
    @app.route('/api/admin/applications')
    def api_admin_applications():
        if session.get('role') != 'admin':
            return jsonify({'error': 'Admin only'}), 403
        safe_apps = []
        for a in app.applications:
            app_safe = a.copy()
            try:
                submitted_at = datetime.fromisoformat(a['submitted_at'])
                app_safe['days_pending'] = max(0, (datetime.now() - submitted_at).days)
            except: app_safe['days_pending'] = 0
            safe_apps.append(app_safe)
        return jsonify(safe_apps)

    # =========================
    # STAFF API
    # =========================
    @app.route('/api/patta/applications')
    def api_applications():
        if session.get('role') not in ['staff', 'admin']:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        search = request.args.get('search', '').upper()
        status = request.args.get('status', '')
        filtered = app.applications[:]
        if search: filtered = [a for a in filtered if search in a.get('ref_id', '')]
        if status: filtered = [a for a in filtered if a.get('status') == status]
        return jsonify(filtered)

    # =========================
    # CITIZEN API
    # =========================
    @app.route('/api/citizen/applications')
    def api_citizen_applications():
        if session.get('role') != 'citizen':
            return jsonify({'success': False, 'error': 'Citizen only'}), 403
        email = session.get('email', '').lower()
        return jsonify([a for a in app.applications if a.get('citizen_email','').lower() == email])

    # =========================
    # CITIZEN FILE UPLOAD
    # =========================
    @app.route('/api/citizen/upload', methods=['POST'])
    def api_citizen_upload():
        if session.get('role') != 'citizen':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Empty filename'}), 400
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({'success': True, 'filename': filename})

    # =========================
    # APPLY PATTA
    # =========================
    @app.route('/api/patta/apply', methods=['POST'])
    def api_apply():
        if session.get('role') != 'citizen':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        form = request.form
        files = request.files
        required_docs = ['parentDoc','saleDeed','aadharCard','encumbCert','layoutScan']
        for d in required_docs:
            if not files.get(d) or files[d].filename == '':
                return jsonify({'success': False, 'error': f'{d} required'}), 400
        ref_id = f"PATTA-{datetime.now().strftime('%Y%m%d')}-{app.next_ref_id:04d}"
        app.next_ref_id += 1
        documents = {}
        for d in required_docs:
            f = files[d]
            filename = secure_filename(f"{ref_id}_{d}_{f.filename}")
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            documents[d] = f"/uploads/{filename}"
        application = {
            'ref_id': ref_id,
            'citizen_email': session.get('email'),
            'district': form.get('district',''),
            'taluk': form.get('taluk',''),
            'village': form.get('village',''),
            'surveyNo': form.get('surveyNo',''),
            'subdivNo': form.get('subdivNo',''),
            'documents': documents,
            'status': 'pending',
            'submitted_at': datetime.now().isoformat()
        }
        app.applications.append(application)
        save_data(app)
        return jsonify({'success': True, 'ref_id': ref_id})

    # =========================
    # UPDATE STATUS
    # =========================
    @app.route('/api/patta/<ref_id>/status', methods=['POST'])
    def api_update_status(ref_id):
        if session.get('role') not in ['staff','admin']:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        try: status = request.get_json(force=True).get('status')
        except: return jsonify({'success': False, 'error':'Invalid JSON'}), 400
        if status not in ['pending','approved','rejected']:
            return jsonify({'success': False, 'error':'Invalid status'}), 400
        for a in app.applications:
            if a['ref_id'] == ref_id:
                a['status'] = status
                if status in ['approved','rejected']:
                    a['approved_by'] = {'name': session.get('name'),'email': session.get('email'),'timestamp': datetime.now().isoformat()}
                save_data(app)
                return jsonify({'success': True, 'status': status})
        return jsonify({'success': False, 'error':'Application not found'}), 404

    # =========================
    # GEMINI CHAT
    # =========================
    @app.route('/api/gemini/chat', methods=['POST'])
    def api_gemini_chat():
        data = request.get_json() or {}
        message = data.get('message','').lower()
        role = session.get('role','guest')
        pending = len([a for a in app.applications if a.get('status')=='pending'])
        total = len(app.applications)
        responses = {
            'guest': {'default':'👋 Login as admin/citizen@test.com (123456)'},
            'citizen': {'hello':f'👋 Welcome! {pending} pending apps','help':'Track/Status/Documents/Submit/Patta'},
            'admin': {'hello':f'👋 Admin! {pending} pending, {total} total','help':'stats/pending/approve/verify/patta'}
        }
        r = responses.get(role,responses['guest'])
        return jsonify({'success': True, 'response': r.get(message,r.get('default'))})

    print("✅ Patta Portal fully loaded!")
    return app
